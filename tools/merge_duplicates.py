"""Merge duplicate records (correlation/merge.py).

  (default)   the verified tier's shadow verdicts: plan only, in a READ ONLY
              transaction: print the counts, write a CSV of every merge and
              every skip to .context/, touch nothing
  --events    record to record: every served record first seen in the last
              --days N (default 7) is paired with its nearest records by the
              founders' gists (cosine >= 0.90, first seen within 72h), and Jev
              judges each pair on the two founding headlines + summaries. Groups
              are stars: a record joins a survivor (most publishers, then
              earliest) only on its own verdict against it (>= 0.85). The dry run
              CALLS JEV — the verdicts are the plan — and stops asking at $1 (a
              week of production is ~$0.40); pairs answered before, in any mode,
              are not asked again. It writes nothing: --apply keeps this run's
              answers in event_match_verdicts (mode 'pair') before merging
  --apply     fold them, most certain first, one transaction each
  --limit N   only the first N merges (a canary: --apply --limit 20, then read
              the survivors before running the rest)
  --resummarise  rebuild merged records whose summary is not their own founder's
              (before 0.0.118.0 a merge could hand a survivor the absorbed
              record's summary: 144 of 878 on 2026-09-29); dry run unless --apply

Idempotent and resumable: a merged copy leaves the plan, and every merge
re-checks itself under the correlation consumer's lock, so a run that stops
anywhere is finished by running it again. Each survivor is queued for the
ordinary analysis pass (the worker spends on it as it would for an attach), so
run --apply where REDIS_URL is production's, i.e. on the worker:

  railway ssh --service worker -- python -m tools.merge_duplicates --apply --limit 20
  railway ssh --service worker -- python -m tools.merge_duplicates --events --apply --limit 20

A dry run from a laptop needs DATABASE_URL (the Postgres public proxy, as
postgresql+asyncpg://); --events also needs OPENROUTER_API_KEY, and a local
REDIS_URL keeps its spend off production's ledger.
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
                "SELECT e.id, e.title, e.first_seen_at, e.projection->>'source_count' AS publishers, "
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
            "absorbed_publishers": a.get("publishers", ""), "survivor_publishers": s.get("publishers", ""),
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


async def _plan_verdicts():
    async with session_scope() as s:
        await s.execute(text("SET TRANSACTION READ ONLY"))
        await s.execute(text("SET LOCAL statement_timeout = '30s'"))
        merges, skips = await merge.plan(s)
    print(f"{len(merges)} merges planned into {len({m.survivor for m in merges})} survivors "
          f"({sum(m.via is not None for m in merges)} resolved through a copy); {len(skips)} skipped")
    for reason, n in Counter(k.reason.split(" (")[0] for k in skips).most_common():
        print(f"  skip {n:4} | {reason}")
    return merges, skips


async def _plan_events(days: int) -> merge.PairPlan:
    p = await merge.plan_events(days=days)
    sizes = Counter(m.survivor for m in p.merges)
    print(f"{p.records} records in {days} days; {p.candidates} gist pairs, {p.reused} answered before")
    print(f"Jev: {p.calls} calls, {p.pairs} pairs (extra direct pairs included), {p.failed} failed, "
          f"{p.unasked} left at the ${merge.PAIR_BUDGET_USD:.2f} cap; cost ${p.cost:.4f}")
    print(f"{len(p.merges)} merges planned into {len(sizes)} survivors"
          + (f"; largest group {max(sizes.values()) + 1} records" if sizes else ""))
    return p


MISMATCHED = """
    SELECT e.id FROM events e
    JOIN event_memberships m ON m.event_id = e.id AND m.match_type = 'new_event'
    JOIN enrichments en ON en.article_id = m.article_id
    WHERE e.merged_into IS NULL
      AND EXISTS (SELECT 1 FROM events c WHERE c.merged_into = e.id)
      AND e.summary IS DISTINCT FROM en.summary
    ORDER BY e.id
"""


# Records an older fold left with two or more founders: the rebuild orders the
# founder first, so a record must have one. The one whose English headline IS
# the record's title keeps it (the title was copied from it), else the earliest.
MULTI_FOUNDER = """
    SELECT m.id, m.event_id,
           row_number() OVER (PARTITION BY m.event_id
                              ORDER BY (en.shared_fields->>'headline' = e.title) DESC NULLS LAST, m.created_at, m.id) AS rank
    FROM event_memberships m
    JOIN events e ON e.id = m.event_id AND e.merged_into IS NULL
    LEFT JOIN enrichments en ON en.article_id = m.article_id
    WHERE m.match_type = 'new_event'
      AND m.event_id IN (SELECT event_id FROM event_memberships WHERE match_type = 'new_event'
                         GROUP BY event_id HAVING count(*) > 1)
"""


async def _resummarise(apply: bool) -> int:
    from correlation.consumer import _rebuild_projection

    async with session_scope() as s:
        multi = (await s.execute(text(MULTI_FOUNDER))).all()
        ids = set((await s.execute(text(MISMATCHED))).scalars().all())
    retag = [r.id for r in multi if r.rank > 1]
    ids |= {r.event_id for r in multi}
    print(f"{len({r.event_id for r in multi})} records have more than one founder ({len(retag)} to retag 'merged'); "
          f"{len(ids)} records to rebuild in all")
    if not apply:
        print("dry run — pass --apply to rebuild them (without moving them up the feed)")
        return 0
    async with session_scope() as s:
        await s.execute(text("UPDATE event_memberships SET match_type = 'merged' WHERE id = ANY(CAST(:i AS uuid[]))"),
                        {"i": [str(i) for i in retag]})
    for eid in sorted(ids):
        await _rebuild_projection(eid, touch=False)
    async with session_scope() as s:
        left = len((await s.execute(text(MISMATCHED))).scalars().all())
    print(f"rebuilt {len(ids)}; {left} still differ")
    return 0


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--events", action="store_true", help="judge records against records (calls Jev, < $1)")
    ap.add_argument("--days", type=int, default=7, help="with --events: records first seen in the last N days")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--resummarise", action="store_true")
    ap.add_argument("--min", type=float, default=None,
                    help="merge floor (default: PRISM_EVENT_VERIFY_MIN); never changes the live attach floor")
    a = ap.parse_args()
    if a.min is not None and not 0.5 <= a.min <= 1.0:
        ap.error("--min is a Jev probability floor between 0.5 and 1.0")
    merge.MERGE_MIN = a.min
    if a.resummarise:
        return await _resummarise(a.apply)

    pairs = None
    if a.events:
        pairs = await _plan_events(a.days)
        merges, skips = pairs.merges, []
    else:
        merges, skips = await _plan_verdicts()
    async with session_scope() as s:
        await s.execute(text("SET TRANSACTION READ ONLY"))
        facts = await _facts(s, {m.absorbed for m in merges} | {m.survivor for m in merges}
                             | {k.absorbed for k in skips} | {k.candidate for k in skips})
    todo = merges[: a.limit] if a.limit is not None else merges

    OUT.mkdir(exist_ok=True)
    path = OUT / f"merge_duplicates{'_events' if a.events else ''}_{datetime.now(UTC):%Y%m%dT%H%M%SZ}.csv"
    _write_csv(path, merges, skips, facts)
    print(f"wrote {path}")
    if not a.apply:
        print("dry run — pass --apply to merge" + (f" the first {len(todo)}" if a.limit is not None else ""))
        return 0

    if pairs is not None:
        await merge.record_pairs(pairs.judged)
        print(f"kept {pairs.pairs} verdicts (event_match_verdicts, mode '{merge.PAIR_MODE}')")
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
