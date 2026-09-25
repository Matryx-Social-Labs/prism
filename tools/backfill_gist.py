"""Embed the gist of every recent article that has none — the verified matching
tier's retrieval vector (correlation/verify.py).

New articles get it at enrichment. This pass covers the window the tier looks
back over (four days) plus margin, so the first shadow day already has
candidates to find instead of only the articles ingested since the deploy.

  (default)  count what would be written; touches nothing
  --apply    write articles.gist_embedding
  --days N   how far back (default 14)

No LLM spend: the gist is text the extractor already wrote (English headline +
one-line summary), embedded locally with the configured model. About 30
articles a second on a laptop (measured: 11,193 in 5.8 minutes, 10 threads).
Run with DATABASE_URL pointing at the database to fill and
PRISM_EMBED_THREADS raised for an offline run.
"""

import argparse
import asyncio
import sys

from sqlalchemy import text

from common.db import get_session_factory
from common.embeddings import embed_texts
from correlation.verify import gist_text

BATCH = 128


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--days", type=int, default=14)
    a = ap.parse_args()
    factory = get_session_factory()
    async with factory() as s:
        rows = (
            await s.execute(
                text(
                    """
                    SELECT a.id, ri.title, en.shared_fields
                    FROM articles a
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    JOIN enrichments en ON en.article_id = a.id
                    WHERE a.gist_embedding IS NULL AND a.created_at > now() - make_interval(days => :d)
                    ORDER BY a.created_at DESC
                    """
                ),
                {"d": a.days},
            )
        ).all()
    todo = [(r.id, g) for r in rows if (g := gist_text(r.shared_fields or {}, r.title or ""))]
    print(f"{len(rows)} articles without a gist in {a.days} days; {len(todo)} have a summary to embed")
    if not a.apply:
        print("dry run — pass --apply to write")
        return 0
    done = 0
    for i in range(0, len(todo), BATCH):
        batch = todo[i : i + BATCH]
        vectors = await embed_texts([g for _, g in batch])
        async with factory() as s:
            await s.execute(
                text("UPDATE articles SET gist_embedding = CAST(:v AS vector) WHERE id = :i"),
                [{"i": str(aid), "v": "[" + ",".join(f"{x:.6f}" for x in vec) + "]"}
                 for (aid, _), vec in zip(batch, vectors, strict=True)],
            )
            await s.commit()
        done += len(batch)
        print(f"  {done}/{len(todo)}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
