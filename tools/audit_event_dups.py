"""How many of production's events are copies of another? Read-only.

The number the verified matching tier (correlation/verify.py) exists to move,
measured the way that tier decides: each event's English headline + summary is
embedded; every event is compared with the earlier events of the four days
before it; the nearest five within the gist floor are put to Jev in one call;
and an event counts as a copy when Jev says >= tau for an earlier event that is
not itself a copy. Grouping is by FOUNDER, never transitive: linking pairs
transitively chained a week of Trump–Xi coverage into one 46-event group.

  uv run python -m tools.audit_event_dups                    # last 7 days, candidates only (free)
  uv run python -m tools.audit_event_dups --judge            # + Jev (~$0.40 for a week, cached)
  uv run python -m tools.audit_event_dups --judge --days 3 --tau 0.7 0.85

Baseline, 2026-09-25 (7 days, 11,193 events, 85% single-article): 17,590
candidate pairs; at tau 0.85, 10.1% of events are copies (1,118 in 756 groups,
the largest 9), and 20 of 20 sampled merges were right. The same pairs linked
transitively would claim 11.5% — and one 46-event chain at 0.7 — which is why
this counts by founder. Jev's answers are cached in .cache/audit_event_dups.json, so a
re-run pays only for new pairs. Production is opened read-only.
"""

from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import asyncpg
import numpy as np

from common.decisions import Noul, decide
from common.embeddings import embed_texts
from correlation.clustering import GIST_CANDIDATES, TIME_WINDOW_DAYS, _scale
from correlation.verify import SAME_HAPPENING
from tools.snapshot_l2 import _prod_url

CACHE = Path(".cache/audit_event_dups.json")


def block(title: str, summary: str, seen) -> str:
    return f"First reported {seen:%Y-%m-%d %H:%M}.\nHeadline: {title}\nSummary: {summary or ''}"


async def load(days: int) -> list[asyncpg.Record]:
    c = await asyncpg.connect(_prod_url(), timeout=90)
    try:
        await c.execute("SET default_transaction_read_only = on")
        return await c.fetch(
            """SELECT e.id::text AS id, e.title, coalesce(e.summary, '') AS summary, e.first_seen_at,
                      (SELECT count(*) FROM event_memberships m WHERE m.event_id = e.id) AS n
               FROM events e WHERE e.headline_by = 'prism' AND e.first_seen_at > now() - make_interval(days => $1)
               ORDER BY e.first_seen_at, e.id""",
            days,
        )
    finally:
        await c.close()


def candidates(rows, vecs: np.ndarray) -> dict[int, list[tuple[int, float]]]:
    """Per event, the earlier in-window events within the gist floor, nearest first."""
    floor = 1.0 - _scale()["gist_candidate"]
    t = np.array([r["first_seen_at"].timestamp() for r in rows])
    out: dict[int, list[tuple[int, float]]] = {}
    for i in range(len(rows)):
        earlier = np.where(t[:i] >= t[i] - TIME_WINDOW_DAYS * 86400)[0]
        if not len(earlier):
            continue
        sims = vecs[earlier] @ vecs[i]
        order = np.argsort(-sims)[:GIST_CANDIDATES]
        near = [(int(earlier[j]), float(sims[j])) for j in order if sims[j] >= floor]
        if near:
            out[i] = near
    return out


async def judge(rows, cands, cache: dict) -> float:
    spend = [0.0]
    sem = asyncio.Semaphore(8)

    async def one(i: int, near: list[tuple[int, float]]) -> None:
        todo = [(j, s) for j, s in near if f"{rows[i]['id']}|{rows[j]['id']}" not in cache]
        if not todo:
            return
        state = {"ARTICLE": block(rows[i]["title"], rows[i]["summary"], rows[i]["first_seen_at"])}
        qs = {}
        for k, (j, _) in enumerate(todo, 1):
            state[f"EVENT_{k}"] = block(rows[j]["title"], rows[j]["summary"], rows[j]["first_seen_at"])
            qs[f"same_{k}"] = Noul(instructions=SAME_HAPPENING.format(a="ARTICLE", b=f"EVENT_{k}"))
        async with sem:
            try:
                d = await decide(state, qs, trace_name="audit-event-dups")
            except Exception:  # noqa: BLE001 — an unjudged pair is simply not counted this run
                return
        spend[0] += d.usage.cost
        for k, (j, _) in enumerate(todo, 1):
            cache[f"{rows[i]['id']}|{rows[j]['id']}"] = d.answers[f"same_{k}"].noul

    items = list(cands.items())
    for x in range(0, len(items), 500):
        await asyncio.gather(*(one(i, near) for i, near in items[x : x + 500]))
        CACHE.write_text(json.dumps(cache))
        print(f"  judged {min(x + 500, len(items))}/{len(items)} events  ${spend[0]:.3f}", flush=True)
    return spend[0]


def founders(rows, cands, cache: dict, tau: float) -> list[int]:
    """root[i]: the founder event i is a copy of, or i itself. An event joins the
    earlier event Jev is surest about, and only one that is not itself a copy."""
    root = list(range(len(rows)))
    for i in range(len(rows)):
        yes = sorted(((cache.get(f"{rows[i]['id']}|{rows[j]['id']}", 0.0), j) for j, _ in cands.get(i, [])), reverse=True)
        for p, j in yes:
            if p >= tau and root[j] == j:
                root[i] = j
                break
    return root


async def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--judge", action="store_true", help="ask Jev (spends; answers cached)")
    ap.add_argument("--tau", type=float, nargs="+", default=[0.85])
    a = ap.parse_args()
    rows = await load(a.days)
    print(f"{len(rows)} events in {a.days} days; {sum(r['n'] == 1 for r in rows) / max(len(rows), 1):.0%} single-article")
    vecs = np.array(await embed_texts([f"{r['title']}. {r['summary']}" for r in rows]), dtype=np.float32)
    cands = candidates(rows, vecs)
    print(f"{sum(len(v) for v in cands.values())} candidate pairs; {len(cands)} events have one")
    if not a.judge:
        print("candidates only — pass --judge to ask Jev")
        return
    CACHE.parent.mkdir(exist_ok=True)
    cache = json.loads(CACHE.read_text()) if CACHE.exists() else {}
    spend = await judge(rows, cands, cache)
    print(f"spent ${spend:.3f} this run")
    for tau in a.tau:
        root = founders(rows, cands, cache, tau)
        copies = sum(1 for i, r in enumerate(root) if r != i)
        groups: dict[int, int] = {}
        for i, r in enumerate(root):
            if r != i:
                groups[r] = groups.get(r, 1) + 1
        print(f"\ntau {tau}: {copies} copies ({copies / max(len(rows), 1):.1%} of events) in {len(groups)} groups")
        for r, n in sorted(groups.items(), key=lambda kv: -kv[1])[:5]:
            print(f"  {n:3} | {rows[r]['title'][:90]}")


if __name__ == "__main__":
    asyncio.run(main())
