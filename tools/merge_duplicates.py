"""Merge the duplicate records the verified tier found in shadow (correlation/merge.py).

  (default)   plan only, in a READ ONLY transaction: print the counts, write a
              CSV of every merge and every skip to .context/, touch nothing
  --apply     fold them, most certain first, one transaction each
  --limit N   only the first N merges (a canary: --apply --limit 20, then read
              the survivors before running the rest)

Idempotent and resumable: a merged copy leaves the plan, and every merge
re-checks itself under the correlation consumer's lock, so a run that stops
anywhere is finished by running it again. No LLM spend here; each survivor is
queued for the ordinary analysis pass (the worker spends on it as it would for
an attach), so run --apply where REDIS_URL is production's, i.e. on the worker:

  railway ssh --service worker -- python -m tools.merge_duplicates --apply --limit 20

A dry run from a laptop needs only DATABASE_URL (the Postgres public proxy, as
postgresql+asyncpg://).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import sys
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import text

from common.db import session_scope
from correlation import merge

OUT = Path(".context")


async def _facts(s, ids: set) -> dict:
    rows = (
        await s.execute(
            text(
                "SELECT e.id, e.title, e.first_seen_at, "
                "(SELECT count(*) FROM event_memberships m WHERE m.event_id = e.id) AS n "
                "FROM events e WHERE e.id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": [str(i) for i in ids]},
        )
    ).mappings().all()
    return {r["id"]: r for r in rows}


def _write_csv(path: Path, merges, skips, facts) -> None:
    def row(action, absorbed, survivor, noul, via=None):
        a, s = facts.get(absorbed, {}), facts.get(survivor, {})
        return {
            "action": action,
            "absorbed_id": absorbed, "survivor_id": survivor, "via_id": via or "",
            "noul": f"{noul:.3f}",
            "absorbed_members": a.get("n", ""), "survivor_members": s.get("n", ""),
            "absorbed_first_seen": a.get("first_seen_at", ""), "survivor_first_seen": s.get("first_seen_at", ""),
            "absorbed_title": a.get("title", ""), "survivor_title": s.get("title", ""),
        }

    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(row("", None, None, 0.0)))
        w.writeheader()
        for m in merges:
            w.writerow(row("merge", m.absorbed, m.survivor, m.noul, m.via))
        for k in skips:
            w.writerow(row(f"skip: {k.reason}", k.absorbed, k.candidate, k.noul))


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    a = ap.parse_args()

    async with session_scope() as s:
        await s.execute(text("SET TRANSACTION READ ONLY"))
        await s.execute(text("SET LOCAL statement_timeout = '30s'"))
        merges, skips = await merge.plan(s)
        facts = await _facts(s, {m.absorbed for m in merges} | {m.survivor for m in merges}
                             | {k.absorbed for k in skips} | {k.candidate for k in skips})
    todo = merges[: a.limit] if a.limit is not None else merges

    OUT.mkdir(exist_ok=True)
    path = OUT / f"merge_duplicates_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.csv"
    _write_csv(path, merges, skips, facts)
    print(f"{len(merges)} merges planned into {len({m.survivor for m in merges})} survivors "
          f"({sum(m.via is not None for m in merges)} resolved through a copy); {len(skips)} skipped")
    for reason, n in Counter(k.reason.split(" (")[0] for k in skips).most_common():
        print(f"  skip {n:4} | {reason}")
    print(f"wrote {path}")
    if not a.apply:
        print("dry run — pass --apply to merge" + (f" the first {len(todo)}" if a.limit is not None else ""))
        return 0

    done = 0
    for i, m in enumerate(todo, 1):
        if await merge.apply(m):
            done += 1
        if i % 50 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)} tried, {done} merged", flush=True)
    print(f"merged {done} of {len(todo)}; {len(todo) - done} had nothing to do or changed since the plan")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
