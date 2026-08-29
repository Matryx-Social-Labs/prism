"""Export the gold-set slice of production as an offline fixture corpus. READ-ONLY.

    uv run python -m tools.export_fixtures

Why this exists: a fresh clone had nothing to look at. `docker compose up` gave
you an empty database, and the only way to see a feed was to enable ingestion
and start paying for LLM calls. That makes the first hour of any contributor's
time cost money and makes every "does this change help?" question unanswerable
offline.

WHAT IS EXPORTED, and why this particular slice: the events named in
tools/gold_stories + tools/gold_labels, plus everything needed to reconstruct
them. That means a fresh clone can run `make seed && make score` and reproduce
the exact numbers this repo argues about, with no API key and no spend.

Enrichments ARE included and embeddings are NOT, on purpose. Enrichment output
is the LLM-expensive artifact — regenerating it costs real money. Embeddings are
produced locally by fastembed for free, so committing ~3 MB of float32 to git to
save a few seconds of CPU is a bad trade.
"""

from __future__ import annotations

import asyncio
import gzip
import json
import os
import re
import subprocess
from pathlib import Path

import asyncpg

from tools.gold_labels import GOLD as GOLD_ARTICLES
from tools.gold_stories import STORY_OF

OUT = Path("tests/fixtures/corpus.json.gz")


def _db_url() -> str:
    raw = os.environ.get("REPAIR_DATABASE_URL")
    if not raw:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=120,
        ).stdout
        raw = next(ln.split("=", 1)[1].strip() for ln in out.splitlines() if ln.startswith("DATABASE_URL="))
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw)


async def export() -> None:
    c = await asyncpg.connect(_db_url(), timeout=120)
    try:
        await c.execute("SET default_transaction_read_only = on")
        # BOTH gold sets, or the fixture serves only one scorer. gold_stories
        # names events; gold_labels names ARTICLES belonging to a different
        # (larger) set of events — the six biggest in production. Exporting only
        # the story events left 156 of 171 labelled articles with no membership
        # and score_clustering scoring 15 articles instead of 171.
        holding = await c.fetch(
            "SELECT DISTINCT event_id::text FROM event_memberships WHERE article_id = ANY($1::uuid[])",
            list(GOLD_ARTICLES),
        )
        events = sorted(set(STORY_OF) | {r["event_id"] for r in holding})
        rows = await c.fetch(
            "SELECT DISTINCT article_id::text FROM event_memberships WHERE event_id = ANY($1::uuid[])",
            events,
        )
        articles = sorted({r["article_id"] for r in rows} | set(GOLD_ARTICLES))

        async def q(sql: str, *args):
            return [dict(r) for r in await c.fetch(sql, *args)]

        data = {
            # Event embeddings ARE included (unlike article-chunk ones): the
            # partition's edge SQL gates on `ea.embedding <=> eb.embedding`, and
            # with NULLs that gate silently passes every pair, so a local
            # partition would not resemble production at all. 152 x 768 floats
            # is a few hundred KB — worth it to make L2 runnable offline.
            "events": await q(
                "SELECT id::text, title, summary, sector, subsector, regions, image_url, "
                "occurred_at::text, first_seen_at::text, last_updated_at::text, projection, "
                "embedding::text AS embedding "
                "FROM events WHERE id = ANY($1::uuid[])", events),
            "articles": await q(
                "SELECT id::text, raw_item_id::text, clean_text, retrieval_tier, word_count "
                "FROM articles WHERE id = ANY($1::uuid[])", articles),
            "raw_items": await q(
                "SELECT ri.id::text, ri.source_id::text, ri.external_id, ri.url, ri.title, ri.body, "
                "ri.language, ri.published_at::text, ri.image_url, ri.relevance, ri.classification "
                "FROM raw_items ri JOIN articles a ON a.raw_item_id = ri.id "
                "WHERE a.id = ANY($1::uuid[])", articles),
            "sources": await q("SELECT id::text, slug, name, source_type, publisher, country, language FROM sources"),
            "enrichments": await q(
                "SELECT id::text, article_id::text, event_type, summary, occurred_at::text, sentiment, "
                "shared_fields, lens_fields, model FROM enrichments WHERE article_id = ANY($1::uuid[])", articles),
            "event_memberships": await q(
                "SELECT event_id::text, article_id::text, match_type, match_score, is_survivor "
                "FROM event_memberships WHERE event_id = ANY($1::uuid[])", events),
            "entities": await q(
                "SELECT DISTINCT e.id::text, e.slug, e.name, e.entity_type FROM entities e "
                "JOIN event_entities ee ON ee.entity_id = e.id WHERE ee.event_id = ANY($1::uuid[])", events),
            "event_entities": await q(
                "SELECT event_id::text, entity_id::text, role FROM event_entities WHERE event_id = ANY($1::uuid[])",
                events),
        }
    finally:
        await c.close()

    # jsonb columns arrive as strings from asyncpg; keep them as parsed objects
    # so the fixture is diffable and the loader does not have to guess.
    for table in ("events", "raw_items", "enrichments"):
        for row in data[table]:
            for k, v in list(row.items()):
                if isinstance(v, str) and v[:1] in "{[" and k in ("projection", "classification",
                                                                  "shared_fields", "lens_fields"):
                    try:
                        row[k] = json.loads(v)
                    except ValueError:
                        pass

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with gzip.open(OUT, "wt", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, sort_keys=True, indent=1)
    size_kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT}  ({size_kb:.0f} KB gzipped)")
    for k, v in data.items():
        print(f"  {k:20} {len(v):5}")


if __name__ == "__main__":
    asyncio.run(export())
