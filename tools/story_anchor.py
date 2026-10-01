"""Running stories: a founder names an ongoing war, dispute, campaign or tournament.

Medal by medal no record is a development of another, and a war's diplomacy,
strikes and oil prices are each their own chain, so the story judge alone leaves
them in dozens of stories (prototype 2026-10-01: Asian Games 109, Iran war 48).
A running story is judged on a one-line scope instead of a founding report.

DRY RUN BY DEFAULT. Creates nothing; lists every persistent story first reported in
the last --days whose founding headline matches --match, with Jev's answer to
"is it part of <scope>?". With --apply: creates the running story (status follows
PRISM_STORIES) and absorbs every story at or above PRISM_STORY_MIN; absorbed
stories redirect to it. New records near its members are judged on its scope
from then on (correlation/stories.py).

    uv run python -m tools.story_anchor --title "Iran war" \\
        --scope "The 2026 Iran war: military, diplomatic and economic developments" \\
        --match "iran|hormuz|tehran|irgc" [--days 30] [--apply]
"""

import argparse
import asyncio
import re
import sys
from types import SimpleNamespace

from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from correlation import stories


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--title", required=True, help="the running story's label")
    ap.add_argument("--scope", required=True, help="one line: the situation, and what counts as part of it")
    ap.add_argument("--match", required=True, help="regex on founding headlines: which stories to ask about")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--apply", action="store_true", help="create the story and absorb (default: dry run)")
    args = ap.parse_args(argv)
    settings = get_settings()
    if settings.prism_stories not in ("shadow", "live"):
        print("PRISM_STORIES is off", file=sys.stderr)
        return 2
    status = "active" if settings.prism_stories == "live" else "shadow"
    pattern = re.compile(args.match, re.I)
    async with session_scope() as s:
        rows = (
            await s.execute(
                text(
                    f"""
                    SELECT st.id, a.id AS anchor, a.title, a.summary, coalesce(a.first_published_at, a.first_seen_at) AS at,
                           (SELECT count(*) FROM story_events x WHERE x.story_id = st.id) AS n
                    FROM stories st JOIN events a ON a.id = st.anchor_event_id
                    WHERE st.merged_into IS NULL AND st.scope IS NULL AND st.status IN (:status, 'dormant')
                      AND coalesce(a.first_published_at, a.first_seen_at) >= now() - interval '{int(args.days)} days'
                    ORDER BY at
                    """
                ),
                {"status": status},
            )
        ).all()
    found = [r for r in rows if pattern.search(r.title or "")]
    print(f"{len(found)} stories match /{args.match}/ of {len(rows)}", flush=True)
    block = f"Running story: {args.scope}"
    verdicts = []
    for r in found:
        rec = SimpleNamespace(id=r.anchor, at=r.at, title=r.title, summary=r.summary)
        try:
            (noul, facet), = (await stories._judge(rec, [block]))[0]
        except Exception as exc:  # noqa: BLE001 — a story the judge could not read stays out
            print(f"  judge failed on {r.title[:60]}: {str(exc)[:80]}", file=sys.stderr)
            continue
        verdicts.append((r, noul, facet))
        mark = "IN " if noul >= settings.prism_story_min else "out"
        print(f"  {mark} {noul:.2f} {facet:13s} [{r.n:3d}] {r.at:%m-%d} {r.title[:80]}", flush=True)
    taking = [(r, n) for r, n, _ in verdicts if n >= settings.prism_story_min]
    print(f"would absorb {len(taking)} stories, {sum(r.n for r, _ in taking)} records")
    if not args.apply or not taking:
        return 0
    async with session_scope() as s:
        anchor = min(taking, key=lambda t: t[0].at)[0].anchor
        running = await stories.create_running_story(s, title=args.title, scope=args.scope, anchor_event_id=anchor)
        moved = sum([await stories.absorb(s, running, r.id) for r, _ in taking])
    print(f"created running story {running}, absorbed {len(taking)} stories, {moved} records")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
