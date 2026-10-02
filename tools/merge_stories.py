"""Fold split stories into the story they are part of, over a backlog
(correlation/story_merge.py). Judges and prints; --apply absorbs.

    uv run python -m tools.merge_stories [--hours 240] [--centroid] [--apply]
"""

import argparse
import asyncio
import sys

from sqlalchemy import text

from common.db import session_scope
from correlation.story_merge import apply_merges, plan_merges


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--hours", type=int, default=240, help="pairs the judge raised in this many hours")
    ap.add_argument("--centroid", action="store_true", help="also pair each small story with the nearest big story")
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args(argv)
    async with session_scope() as session:
        merges = await plan_merges(session, hours=args.hours, centroid=args.centroid)
        titles = dict((await session.execute(text(
            "SELECT s.id, coalesce(s.scope, s.label) FROM stories s WHERE s.id = ANY(CAST(:i AS uuid[]))"),
            {"i": [str(x) for m in merges for x in (m["story"], m["into"])]})).all())
    for m in merges:
        print(f"{min(m['parts']):.2f}  ({m['records']}) {titles.get(m['story'], '')[:70]}\n      -> {titles.get(m['into'], '')[:90]}")
    print(f"\n{len(merges)} merges, {sum(m['records'] for m in merges)} records")
    if args.apply:
        async with session_scope() as session:
            print(f"applied {await apply_merges(session, merges)}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
