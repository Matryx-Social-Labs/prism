"""Fill events.first_published_at for the records that predate it, and turn
leads_to links the right way round (correlation/chronology.py).

Every projection rebuild keeps both from migration c7d4e9a2b815 on; this is for
the records and links no rebuild will touch again.

    DATABASE_URL=postgresql+asyncpg://… uv run python -m tools.backfill_first_published          # dry run
    DATABASE_URL=postgresql+asyncpg://… uv run python -m tools.backfill_first_published --apply

The dry run cannot write (its transaction is READ ONLY) and runs before the
migration as well: it reports what the column would hold. --apply needs the
migration, writes --batch records per transaction, and is idempotent: a record
already holding its value is not rewritten, so a re-run writes nothing.
"""

from __future__ import annotations

import argparse
import asyncio
import sys

from sqlalchemy import text

from common.db import session_scope
from correlation.chronology import FIRST_PUBLISHED, ORIENT_ALL, migrated

# When the column is absent (dry run before the migration) every record would be written.
_PLAN_RECORDS = """
    WITH f AS (SELECT e.first_seen_at, {current} AS current, {fp} AS fp FROM events e)
    SELECT count(*) AS records,
           count(*) FILTER (WHERE current IS DISTINCT FROM fp) AS to_write,
           count(*) FILTER (WHERE fp = first_seen_at) AS undated,
           count(*) FILTER (WHERE first_seen_at - fp > interval '6 hours') AS late_6h,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY extract(epoch FROM first_seen_at - fp) / 3600) AS median_h
    FROM f
"""

_PLAN_LINKS = f"""
    SELECT l.method, count(*) AS links,
           count(*) FILTER (WHERE f.fp > t.fp) AS backwards,
           count(*) FILTER (WHERE f.fp > t.fp AND EXISTS (
               SELECT 1 FROM event_links r WHERE r.from_event_id = l.to_event_id AND r.to_event_id = l.from_event_id
           )) AS stuck
    FROM event_links l
    CROSS JOIN LATERAL (SELECT {FIRST_PUBLISHED} AS fp FROM events e WHERE e.id = l.from_event_id) f
    CROSS JOIN LATERAL (SELECT {FIRST_PUBLISHED} AS fp FROM events e WHERE e.id = l.to_event_id) t
    WHERE l.relation = 'leads_to'
    GROUP BY l.method ORDER BY l.method
"""

_WRITE = text(
    f"""
    UPDATE events e SET first_published_at = v.fp
    FROM (SELECT e.id, {FIRST_PUBLISHED} AS fp FROM events e WHERE e.id = ANY(CAST(:ids AS uuid[]))) v
    WHERE e.id = v.id AND e.first_published_at IS DISTINCT FROM v.fp
    """
)


async def plan() -> None:
    async with session_scope() as s:
        await s.execute(text("SET TRANSACTION READ ONLY"))
        has = await migrated(s)
        current = "e.first_published_at" if has else "NULL::timestamptz"
        r = (await s.execute(text(_PLAN_RECORDS.format(current=current, fp=FIRST_PUBLISHED)))).mappings().one()
        links = (await s.execute(text(_PLAN_LINKS))).mappings().all()
    print(f"column present: {has}")
    print(f"records: {r['records']}; to write: {r['to_write']}")
    print(f"  no member report inside the window (keeps first_seen_at): {r['undated']}")
    print(f"  first reported more than 6h before Prism first saw it: {r['late_6h']}; "
          f"median gap {r['median_h'] or 0:.2f}h")
    for row in links:
        print(f"leads_to links ({row['method']}): {row['links']}; backwards: {row['backwards']}, "
              f"of which stored both ways round and left: {row['stuck']}")


async def apply(batch: int) -> None:
    written, after = 0, "00000000-0000-0000-0000-000000000000"
    while True:
        async with session_scope() as s:
            ids = (
                await s.execute(
                    text("SELECT id::text FROM events WHERE id > CAST(:after AS uuid) ORDER BY id LIMIT :n"),
                    {"after": after, "n": batch},
                )
            ).scalars().all()
            if not ids:
                break
            written += (await s.execute(_WRITE, {"ids": list(ids)})).rowcount
        after = ids[-1]
        print(f"  … through {after}: {written} written")
    async with session_scope() as s:
        flipped = (await s.execute(ORIENT_ALL)).rowcount
    print(f"wrote first_published_at on {written} records; turned {flipped} leads_to links the right way round")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--batch", type=int, default=2000)
    a = ap.parse_args()
    await plan()
    if not a.apply:
        print("dry run — pass --apply to write")
        return 0
    async with session_scope() as s:
        if not await migrated(s):
            print("refusing: events.first_published_at does not exist; run the migration (c7d4e9a2b815) first")
            return 1
    await apply(a.batch)
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
