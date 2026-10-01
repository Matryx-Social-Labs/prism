"""Place the backlog in stories: every live record without one, in first-report order.

Runs correlation/stories.assign_story on each record, oldest report first, so a
record only ever sees the stories of what was reported before it — the same
order the live sweeper would have seen. PRISM_STORIES sets the mode: `shadow`
writes stories nobody is served (the dry run: read them, then score them with
tools/audit_stories), `live` writes served ones. Refuses to run with it off.

Idempotent: a placed record is skipped. --reset-shadow deletes every shadow story
first (story_events and story_verdicts go with it), to re-run after a change.
One Jev call per record with a nearby story (~$0.00004).

    PRISM_STORIES=shadow uv run python -m tools.assign_stories --days 14 [--limit N] [--reset-shadow]
"""

import argparse
import asyncio
import sys
import time

from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from correlation.stories import assign_story


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--days", type=int, default=14, help="records first reported in the last N days")
    ap.add_argument("--limit", type=int, default=0, help="stop after N records (0 = all)")
    ap.add_argument("--reset-shadow", action="store_true", help="delete every shadow story first")
    args = ap.parse_args(argv)
    mode = get_settings().prism_stories
    if mode not in ("shadow", "live"):
        print("PRISM_STORIES is off: set shadow (dry run) or live", file=sys.stderr)
        return 2
    if args.reset_shadow:
        async with session_scope() as s:
            n = (await s.execute(text("DELETE FROM stories WHERE status = 'shadow'"))).rowcount
        print(f"deleted {n} shadow stories")
    async with session_scope() as s:
        ids = (
            await s.execute(
                text(
                    f"""
                    SELECT e.id FROM events e
                    WHERE e.merged_into IS NULL
                      AND coalesce(e.first_published_at, e.first_seen_at) >= now() - interval '{int(args.days)} days'
                      AND NOT EXISTS (SELECT 1 FROM story_events se WHERE se.event_id = e.id)
                    ORDER BY coalesce(e.first_published_at, e.first_seen_at), e.id
                    """
                )
            )
        ).scalars().all()
    if args.limit:
        ids = ids[: args.limit]
    print(f"{len(ids)} records to place, mode {mode}", flush=True)
    started, failed = time.time(), 0
    for k, eid in enumerate(ids, 1):
        try:
            async with session_scope() as s:
                await assign_story(s, eid)
        except Exception as exc:  # noqa: BLE001 — report and go on; a rerun places what is left
            failed += 1
            print(f"failed {eid}: {str(exc)[:160]}", file=sys.stderr, flush=True)
        if k % 200 == 0:
            print(f"{k}/{len(ids)} placed, {failed} failed, {time.time() - started:.0f}s", flush=True)
    async with session_scope() as s:
        row = (
            await s.execute(
                text(
                    """
                    SELECT count(*) AS stories,
                           count(*) FILTER (WHERE n >= 2) AS with_two,
                           max(n) AS biggest
                    FROM (SELECT story_id, count(*) AS n FROM story_events se
                          JOIN stories st ON st.id = se.story_id AND st.status = :status
                          GROUP BY story_id) t
                    """
                ),
                {"status": "shadow" if mode == "shadow" else "active"},
            )
        ).one()
    print(f"done: {len(ids) - failed} placed, {failed} failed; {row.stories} stories, "
          f"{row.with_two} with 2+ records, biggest {row.biggest}")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
