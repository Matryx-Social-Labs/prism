"""Recount every event's `projection.source_count` as distinct publishers.

It counted member ARTICLES until audit P0 #8 (2026-09-27): one outlet re-filing a
story, or carrying it on several section feeds, read as corroboration, so a
five-article Indian Express record led the front page as the most-corroborated.
The correlation rebuild now writes the publisher count; this pass repairs events
written before, which nothing else touches until they gain a member.

    uv run python -m tools.backfill_source_count            # dry run: how many change, old → new
    uv run python -m tools.backfill_source_count --apply    # write them

The recount is the rebuild's own: members with an enrichment, one per
COALESCE(publisher, slug). Only the one key is written, only where it differs,
so a rerun is a no-op. No revision is kept (a count is not a new version,
migration e7a4c2b9f613) and last_updated_at is left alone, so the sitemap's
lastmod and the feed's clocks do not move. Stories need nothing: trending
already counts publishers when it writes stories.source_count.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
import uuid
from collections import Counter

from sqlalchemy import text

from common.db import session_scope

# Only events a rebuild has written (projection carries the key): the recount
# must not invent a projection for a row that never had one.
RECOUNT = """
    SELECT e.id, (e.projection ->> 'source_count')::int AS old, c.n AS new
    FROM events e
    JOIN (
        SELECT em.event_id, count(DISTINCT COALESCE(s.publisher, s.slug))::int AS n
        FROM event_memberships em
        JOIN articles a ON a.id = em.article_id
        JOIN enrichments en ON en.article_id = a.id
        JOIN raw_items ri ON ri.id = a.raw_item_id
        JOIN sources s ON s.id = ri.source_id
        GROUP BY em.event_id
    ) c ON c.event_id = e.id
    WHERE e.projection ? 'source_count'
      AND (e.projection ->> 'source_count')::int IS DISTINCT FROM c.n
"""


async def recount(session, *, apply: bool) -> list[tuple[uuid.UUID, int, int]]:
    """(event id, stored count, publisher count) for every event that differs;
    with apply, writes the publisher count into those events."""
    rows = [(r[0], r[1], r[2]) for r in (await session.execute(text(RECOUNT))).all()]
    if apply and rows:
        await session.execute(
            text(
                "UPDATE events e SET projection = e.projection || jsonb_build_object('source_count', c.new) "
                f"FROM ({RECOUNT}) c WHERE e.id = c.id"
            )
        )
    return rows


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    async with session_scope() as session:
        rows = await recount(session, apply=args.apply)
    total = len(rows)
    to_one = sum(1 for _, old, new in rows if old > 1 and new == 1)
    print(f"{total} events change; {to_one} of them passed as multi-source (≥2) with one publisher")
    for (old, new), n in Counter((old, new) for _, old, new in rows).most_common(15):
        print(f"  {old:>3} → {new:<3} {n}")
    print("written" if args.apply else "dry run — pass --apply to write")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
