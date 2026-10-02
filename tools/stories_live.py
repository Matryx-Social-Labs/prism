"""Turn the persistent stories live (correlation/stories.py), or back.

Run right after PRISM_STORIES=live reaches the worker (plan §12). Everything
happens in one transaction; without --apply it is rolled back after printing
what it did, so the dry run is the real run, unkept.

  1. every judge-built story lists its records (member_event_ids from
     story_events); a shadow story turns dormant, an absorbed one keeps its
     merged_into and redirects;
  2. refresh_stories(everything=True): counts, listing state, hero, cast, label;
  3. each Leiden story whose records sit at least half in one judge-built story
     redirects there (merged_into, dormant), so an old link opens the new story.

--revert puts every judge-built story back in shadow and restores the Leiden
rows the journal names. Run it with PRISM_STORIES=shadow on the worker.

    uv run python -m tools.stories_live [--apply] [--journal PATH]
    uv run python -m tools.stories_live --revert PATH [--apply]
"""

import argparse
import asyncio
import json
import sys
import time

from sqlalchemy import text

from common.db import session_scope
from correlation.stories import refresh_stories

LIST = """
UPDATE stories st SET member_event_ids = coalesce((
        SELECT jsonb_agg(se.event_id::text ORDER BY se.event_id)
        FROM story_events se JOIN events e ON e.id = se.event_id AND e.merged_into IS NULL
        WHERE se.story_id = st.id), '[]'::jsonb),
    status = CASE WHEN st.status = 'shadow' THEN 'dormant' ELSE st.status END
WHERE st.anchor_event_id IS NOT NULL
"""

# Each unmerged Leiden story, and the judge-built story (followed through
# absorptions) holding the most of its records, when that is at least half.
MAJORITY = """
WITH RECURSIVE canon(id, root) AS (
    SELECT id, id FROM stories WHERE anchor_event_id IS NOT NULL AND merged_into IS NULL
    UNION ALL
    SELECT s.id, c.root FROM stories s JOIN canon c ON s.merged_into = c.id WHERE s.anchor_event_id IS NOT NULL
),
lm AS (
    SELECT l.id AS leiden, jsonb_array_length(l.member_event_ids) AS n, CAST(x AS uuid) AS event_id
    FROM stories l, jsonb_array_elements_text(l.member_event_ids) AS x
    WHERE l.anchor_event_id IS NULL AND l.merged_into IS NULL
),
votes AS (
    SELECT lm.leiden, lm.n, c.root, count(*) AS k
    FROM lm JOIN story_events se ON se.event_id = lm.event_id JOIN canon c ON c.id = se.story_id
    GROUP BY lm.leiden, lm.n, c.root
)
SELECT DISTINCT ON (leiden) leiden, root, k, n FROM votes WHERE k * 2 >= n ORDER BY leiden, k DESC, root
"""

TOP = """
SELECT st.slug, st.label, st.velocity, st.source_count, jsonb_array_length(st.member_event_ids) AS n,
       st.scope IS NOT NULL AS running
FROM stories st WHERE st.status = 'active' AND st.merged_into IS NULL
ORDER BY (st.scope IS NOT NULL) DESC, st.velocity DESC, st.source_count DESC, st.last_updated_at DESC
LIMIT 20
"""


async def go_live(session, journal: dict) -> None:
    journal["v3"] = [dict(r) for r in (await session.execute(text(
        "SELECT id::text, status, merged_into::text FROM stories WHERE anchor_event_id IS NOT NULL"))).mappings()]
    journal["leiden"] = [dict(r) for r in (await session.execute(text(
        "SELECT id::text, status, merged_into::text FROM stories WHERE anchor_event_id IS NULL"))).mappings()]
    listed = (await session.execute(text(LIST))).rowcount
    print(f"1. judge-built stories listing their records: {listed}")
    t0 = time.monotonic()
    active = await refresh_stories(session, everything=True)
    print(f"2. refreshed in {time.monotonic() - t0:.0f} s: {active} listed on /trending")
    pairs = (await session.execute(text(MAJORITY))).all()
    for leiden, root, _, _ in pairs:
        await session.execute(text("UPDATE stories SET merged_into = :r, status = 'dormant' WHERE id = :l"),
                              {"r": str(root), "l": str(leiden)})
    left = len([r for r in journal["leiden"] if r["merged_into"] is None]) - len(pairs)
    print(f"3. Leiden stories redirected to a judge-built story: {len(pairs)}; left as they were: {left}")
    print("\nTOP OF /trending")
    for r in (await session.execute(text(TOP))).all():
        print(f"  {'RUNNING ' if r.running else ''}v{r.velocity:.0f} · {r.source_count} outlets · {r.n} records  {r.label[:80]}")


async def revert(session, journal: dict) -> None:
    n = (await session.execute(text(
        "UPDATE stories SET status = 'shadow', member_event_ids = '[]'::jsonb WHERE anchor_event_id IS NOT NULL"))).rowcount
    await session.execute(
        text("UPDATE stories s SET status = j.status, merged_into = CAST(j.merged_into AS uuid) "
             "FROM jsonb_to_recordset(CAST(:j AS jsonb)) AS j(id text, status text, merged_into text) "
             "WHERE s.id = CAST(j.id AS uuid)"),
        {"j": json.dumps(journal["leiden"])},
    )
    print(f"judge-built stories back in shadow: {n}; Leiden rows restored: {len(journal['leiden'])}")


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--journal", default=f"stories_live_{int(time.time())}.json")
    ap.add_argument("--revert", metavar="JOURNAL")
    args = ap.parse_args(argv)
    async with session_scope() as session:
        if args.revert:
            with open(args.revert) as f:
                await revert(session, json.load(f))
        else:
            journal: dict = {}
            await go_live(session, journal)
            if args.apply:
                with open(args.journal, "w") as f:
                    json.dump(journal, f)
                print(f"journal: {args.journal}")
        if not args.apply:
            await session.rollback()
            print("\ndry run: rolled back, nothing kept")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
