"""Recover the reported claims the direct-only gate dropped at write time.

#226 made the write-time gate keep only words inside quotation marks (live on
prod from 27 Sep 2026, 19:26 UTC); #241 also keeps, for an Indian-language
article, the words it reports with a speech verb beside the speaker's name.
Indian-language articles enriched in between lost those claims when stored.

The extractor's own output is still on every row (`enrichments.raw_model_output`
holds the claims as the model returned them, before the gate), so recovery
re-runs TODAY's gate (enrichment/claims.verify_claims, with the article's
language) on it. No model is asked: it costs nothing, needs no API key, and
gives exactly the claims the live gate would store now — a fresh extraction
would re-roll the model and could drop quotes the row already has.

Only `shared_fields.claims` is written (jsonb_set). Summary, entities, lens
fields, tickers, cyber facts and the raw output are not read or written. No
projection is rebuilt: an event's projection holds no claims — the record reads
them from the enrichments on each request (api/routes/events.group_claims).

    DATABASE_URL=postgresql+asyncpg://… uv run python -m tools.backfill_reported_claims            # dry run
    DATABASE_URL=postgresql+asyncpg://… uv run python -m tools.backfill_reported_claims --apply

Idempotent: an article whose stored claims already hold everything today's gate
keeps is not selected. The dry run's transaction is READ ONLY.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from datetime import datetime

from sqlalchemy import text

from common.db import session_scope
from enrichment.claims import REPORTED_LANGS, verify_claims
from enrichment.schemas import ArticleExtraction

# When #226's direct-only gate reached prod.
SINCE = "2026-09-27T19:26:00+00:00"

CANDIDATES = text(
    """
    SELECT e.id, ri.language AS lang, a.clean_text, e.shared_fields -> 'claims' AS stored, e.raw_model_output AS raw,
           (SELECT count(DISTINCT em.event_id) FROM event_memberships em WHERE em.article_id = a.id) AS events
    FROM enrichments e
    JOIN articles a ON a.id = e.article_id
    JOIN raw_items ri ON ri.id = a.raw_item_id
    WHERE e.created_at >= :since AND ri.language = ANY(:langs)
      AND jsonb_typeof(e.raw_model_output -> 'shared' -> 'claims') = 'array'
      AND jsonb_array_length(e.raw_model_output -> 'shared' -> 'claims') > 0
    ORDER BY e.created_at
    """
)
# Guarded on the claims read: a row changed since (a re-extraction) is left alone.
WRITE = text(
    "UPDATE enrichments SET shared_fields = jsonb_set(shared_fields, '{claims}', CAST(:claims AS jsonb)) "
    "WHERE id = :id AND shared_fields -> 'claims' IS NOT DISTINCT FROM CAST(:stored AS jsonb)"
)


def recovered(row: dict) -> tuple[list[dict], list[dict]]:
    """Today's gate over the extractor's own claims: every claim it keeps, and
    those the row lacks (none when there is nothing to recover)."""
    try:
        claims = ArticleExtraction.model_validate(row["raw"]).shared.claims
    except ValueError:  # a raw output an older extractor wrote in another shape: nothing to recover
        return [], []
    kept, _ = verify_claims(claims, row["clean_text"] or "", row["lang"])
    have = {(c.get("speaker"), c.get("quote_text")) for c in row["stored"] or [] if isinstance(c, dict)}
    new = [c.model_dump() for c in kept]
    return new, [c for c in new if (c["speaker"], c["quote_text"]) not in have]


async def run(since: datetime, *, apply: bool) -> dict:
    """Select, and with `apply` write. Returns what was (or would be) recovered."""
    async with session_scope() as s:
        if not apply:
            await s.execute(text("SET TRANSACTION READ ONLY"))
        rows = [dict(r) for r in (await s.execute(CANDIDATES, {"since": since, "langs": sorted(REPORTED_LANGS)})).mappings()]
        plan = [(r, *recovered(r)) for r in rows]
        plan = [(r, new, added) for r, new, added in plan if added]
        written = 0
        if apply:
            for r, new, _ in plan:
                result = await s.execute(WRITE, {"id": r["id"], "claims": json.dumps(new, ensure_ascii=False),
                                                 "stored": json.dumps(r["stored"], ensure_ascii=False)})
                written += result.rowcount
    return {
        "scanned": len(rows),
        "articles": len(plan),
        "claims": sum(len(added) for *_, added in plan),
        "by_lang": Counter(r["lang"] for r, *_ in plan),
        "events": sum(r["events"] for r, *_ in plan),
        "written": written,
        "cost": 0.0,  # no model call
        "sample": [(c["speaker"], c["quote_text"]) for *_, added in plan for c in added][:10],
    }


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--since", default=SINCE, help=f"enrichments created from this time (ISO, default {SINCE})")
    ap.add_argument("--apply", action="store_true", help="write the recovered claims; without it nothing is")
    args = ap.parse_args()
    r = await run(datetime.fromisoformat(args.since), apply=args.apply)
    print(f"Indian-language articles enriched since {args.since} with the extractor's claims on file: {r['scanned']}")
    print(f"  whose stored claims lack what today's gate keeps: {r['articles']} "
          f"({', '.join(f'{k} {v}' for k, v in r['by_lang'].most_common())}), in {r['events']} event memberships")
    print(f"  claims recovered: {r['claims']} · cost ${r['cost']:.2f} (no model call)")
    for speaker, quote in r["sample"]:
        print(f"    {speaker}: {quote[:90]}")
    if not args.apply:
        print("\nDRY RUN — nothing was written. Re-run with --apply.")
    else:
        print(f"\nwrote the claims of {r['written']} articles; every other field untouched")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
