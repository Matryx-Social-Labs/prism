"""Score the persistent stories (correlation/stories.py) before anyone is served them.

Read-only. For the stories of one status (shadow while PRISM_STORIES=shadow):
  - size distribution, the largest stories with their founding headline and facets;
  - for each watched story (a name and a title regex over records), how many
    stories its records sit in and what share the largest holds — fragmentation;
  - a random sample of judge attaches (record → story) written to a sheet for a
    blind read (the attach-precision gate, plan B7).
The regexes are a coarse net over English record titles: a "foreign" member of the
largest story is often a record the regex missed, so read them before counting.

    uv run python -m tools.audit_stories [--status shadow] [--days 9] [--sample 60]
        [--watch "flydubai=flydubai|fz ?1073|machch?h?ar"] ...
"""

import argparse
import asyncio
import collections
import random
import re
import sys

from sqlalchemy import text

from common.db import session_scope

WATCH = {
    "flydubai": r"flydubai|fly dubai|fz ?1073|machch?h?ar|machar|matchar",
    "iran_war": r"\biran|hormuz|tehran|khamenei|araghchi|pezeshkian|irgc",
    "asian_games": r"asian games|asiad",
    "ukraine_war": r"ukrain|zelensk|kyiv|kremlin",
}
NOT_IRAN_WAR = r"kabaddi|irani cup|bus crash|lashes|malware|kiran|asian games|flydubai"


async def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--status", default="shadow")
    ap.add_argument("--days", type=int, default=9)
    ap.add_argument("--sample", type=int, default=60)
    ap.add_argument("--sheet", default=".context/story_attach_sample.txt")
    ap.add_argument("--watch", action="append", default=[], help="name=regex (adds to the defaults)")
    args = ap.parse_args(argv)
    watch = dict(WATCH, **dict(w.split("=", 1) for w in args.watch))
    async with session_scope() as s:
        rows = (
            await s.execute(
                text(
                    f"""
                    SELECT se.event_id, se.story_id, se.noul, se.facet, e.title,
                           (st.anchor_event_id = se.event_id) AS is_anchor, st.scope,
                           a.title AS anchor_title
                    FROM story_events se
                    JOIN stories st ON st.id = se.story_id AND st.status = :status AND st.merged_into IS NULL
                    JOIN events e ON e.id = se.event_id AND e.merged_into IS NULL
                    LEFT JOIN events a ON a.id = st.anchor_event_id
                    WHERE coalesce(e.first_published_at, e.first_seen_at) >= now() - interval '{int(args.days)} days'
                    """
                ),
                {"status": args.status},
            )
        ).all()
    if not rows:
        print(f"no {args.status} stories in the last {args.days} days")
        return 1
    members = collections.defaultdict(list)
    for r in rows:
        members[r.story_id].append(r)
    sizes = sorted((len(v) for v in members.values()), reverse=True)
    print(f"{len(rows)} records in {len(members)} {args.status} stories: "
          f"{sum(n >= 2 for n in sizes)} with 2+, {sum(n >= 10 for n in sizes)} with 10+, largest {sizes[:10]}")
    print("\nLARGEST")
    for mem in sorted(members.values(), key=len, reverse=True)[:15]:
        facets = collections.Counter(m.facet for m in mem)
        name = mem[0].scope or mem[0].anchor_title or "?"
        print(f"  [{len(mem):3d}] {name[:80]}\n        " + " · ".join(f"{f} {n}" for f, n in facets.most_common()))
    print("\nWATCHED (share of the matching records in their largest story)")
    story_of = {r.event_id: r.story_id for r in rows}
    title_of = {r.event_id: r.title or "" for r in rows}
    for name, rx in watch.items():
        hit = {e for e, t in title_of.items() if re.search(rx, t, re.I)
               and not (name == "iran_war" and re.search(NOT_IRAN_WAR, t, re.I))}
        if not hit:
            continue
        counts = collections.Counter(story_of[e] for e in hit)
        big, n = counts.most_common(1)[0]
        print(f"  {name:12s} {len(hit):4d} records in {len(counts):3d} stories; largest holds {n / len(hit):.0%} "
              f"(story size {len(members[big])})")
    attaches = [r for r in rows if not r.is_anchor and r.noul is not None]
    random.seed(7)
    sample = random.sample(attaches, min(args.sample, len(attaches)))
    with open(args.sheet, "w") as f:
        for k, r in enumerate(sample, 1):
            story = members[r.story_id][0]
            f.write(f"{k:2d}. part={r.noul:.2f} facet={r.facet}\n    RECORD: {r.title}\n"
                    f"    STORY ({len(members[r.story_id])}): {story.scope or story.anchor_title}\n")
    print(f"\n{len(attaches)} judge attaches; {len(sample)} sampled blind to {args.sheet}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
