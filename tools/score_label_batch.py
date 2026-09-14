"""Score the CURRENT story layer against the adjudicated gold set. Read-only.

    uv run python -m tools.score_label_batch --as-of 2026-08-04              # committed gold
    uv run python -m tools.score_label_batch --as-of 2026-08-04 --agreed-only
    uv run python -m tools.score_label_batch --batch <key> --as-of ...      # a live batch

The default reads tools/gold_story_pairs — the adjudicated, version-controlled set —
so a number quoted from here is reproducible from the repo alone. `--batch` reads a
live labelling batch instead, for work still in progress; it applies the three
adjudication rules because a live batch has no adjudication yet.

WHY --as-of EXISTS. The partitioner keeps a rolling `STORY_WINDOW_DAYS` window on
`last_updated_at`, so a gold set stops being scoreable about a month after it is
labelled: its events slide out and the join returns nothing. That is not a
theoretical worry — scoring the 45-story gold set against the live partition
matched 2 of 86 events and printed P 0 / R 0 / F1 0, which reads as a total
regression rather than as an empty join. Pass the date the corpus was frozen and
the window is reconstructed as it stood then.

WHY IT REBUILDS THE GRAPH rather than reading `event_story`. `event_story` only
ever holds the LIVE partition, so it cannot answer "how would today's algorithm
have grouped the events this gold set covers". The graph is rebuilt through the
same `_load_*` + `merge_edges` + `leiden_partition` path production uses, so a
change to the story layer shows up here without the scorer being updated.

READ THE NUMBERS THE WAY tools/score_stories DOES:
  - PRECISION is over-merging, RECALL is over-splitting.
  - Cdet weights a false alarm 4x a miss (TDT convention): a wrong merge fuses
    two stories on one card and a reader sees it; a miss is a duplicate card.
  - Pairwise scores over-predict the benefit of tightening — they are stateless
    and cannot see one dropped edge cascade into a three-way split. Replay before
    shipping anything this suggests.

Scoring is restricted to the pairs a human actually judged (seed x candidate),
not all pairs in the window, so a story the batch never asked about cannot
silently count as a true negative.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
from datetime import UTC, datetime

from sqlalchemy import text

C_MISS, C_FA = 1.0, 4.0


def _prod_url() -> str:
    raw = os.environ.get("REPAIR_DATABASE_URL")
    if not raw:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=120,
        ).stdout
        for line in out.splitlines():
            if line.startswith("DATABASE_URL="):
                raw = line.split("=", 1)[1].strip()
                break
    if not raw:
        raise SystemExit("no database url (set REPAIR_DATABASE_URL)")
    return re.sub(r"^postgres(ql)?(\+asyncpg)?://", "postgresql+asyncpg://", raw)


def _jl(x):
    return json.loads(x) if isinstance(x, str) else x


def _cand_ids(c) -> list[str]:
    return [
        str(x.get("id") or x.get("event_id")) if isinstance(x, dict) else str(x)
        for x in (_jl(c) or [])
    ]


def _sel_ids(s) -> set[str]:
    s = _jl(s)
    if isinstance(s, list):
        return {str(x) for x in s}
    return {str(s)} if s else set()


def _score(judged, labels, title):
    """judged: [((a,b), gold_bool)]; labels: {event_id: story_label}."""
    tp = fp = fn = tn = 0
    unplaced = 0
    for (a, b), gold in judged:
        if a not in labels or b not in labels:
            unplaced += 1
            continue
        pred = labels[a] == labels[b]
        if pred and gold:
            tp += 1
        elif pred and not gold:
            fp += 1
        elif gold:
            fn += 1
        else:
            tn += 1
    scored = tp + fp + fn + tn
    print(f"\n{title}")
    if not scored:
        print(f"  NOTHING SCORABLE — all {unplaced} pairs fell outside the window. "
              f"Check --as-of.")
        return
    P = tp / (tp + fp) if tp + fp else 0.0
    R = tp / (tp + fn) if tp + fn else 0.0
    F = 2 * P * R / (P + R) if P + R else 0.0
    npos, nneg = tp + fn, fp + tn
    cdet = C_MISS * (fn / npos if npos else 0) + C_FA * (fp / nneg if nneg else 0)
    print(f"  {scored} pairs scored ({npos} same-story, {nneg} not); "
          f"{unplaced} skipped as outside the window")
    print(f"  P {P:.4f}   R {R:.4f}   F1 {F:.4f}   Cdet {cdet:.4f}")
    print(f"  tp {tp}  fp {fp} (wrong merges)  fn {fn} (wrong splits)")


async def main(batch: str | None, as_of: str | None, resolution: float | None,
               agreed_only: bool = False) -> None:
    os.environ["DATABASE_URL"] = _prod_url()

    import correlation.partition as P
    from common.db import session_scope

    when = datetime.fromisoformat(as_of).replace(tzinfo=UTC) if as_of else None
    res = resolution if resolution is not None else P.LEIDEN_RESOLUTION_V2

    async with session_scope() as s:
        nodes = await P._load_nodes(s, when)
        entity_edges = await P._load_edges(s, when)
        emb_edges = await P._load_embedding_edges(s, when)
        rows = [] if batch is None else (await s.execute(
            text("""
                SELECT i.name AS who, t.seed_event_id::text AS seed,
                       t.candidates, r.selected
                FROM label_responses r
                JOIN label_invites i ON i.id = r.invite_id
                JOIN label_tasks t ON t.id = r.task_id
                JOIN label_batches b ON b.id = t.batch_id
                WHERE b.key = :k
            """), {"k": batch},
        )).mappings().all()

    edges = P.merge_edges(entity_edges, emb_edges)
    labels = {k: str(v) for k, v in P.leiden_partition(nodes, edges, res).items()}
    sizes = {}
    for v in labels.values():
        sizes[v] = sizes.get(v, 0) + 1
    print(f"window as-of {as_of or 'now'}: {len(nodes)} events, "
          f"{len(entity_edges)} entity + {len(emb_edges)} embedding edges "
          f"-> {len(edges)} merged")
    print(f"partition at resolution {res}: {len(sizes)} stories, "
          f"largest {max(sizes.values()) if sizes else 0}, "
          f"{sum(1 for n in sizes.values() if n > 25)} over Story Forest's max of 25")

    if batch is None:
        from tools import gold_story_pairs as G

        gold = G.pairs(include_adjudicated=not agreed_only)
        print(f"\ngold: tools/gold_story_pairs, adjudicated {G.ADJUDICATED_ON} — "
              f"{len(gold)} pairs, {sum(gold.values())} positive"
              + (" (agreed-only)" if agreed_only else ""))
        _score(list(gold.items()), labels, "CURRENT STORY LAYER vs adjudicated gold")
        return

    verdict: dict[tuple[str, str], dict[str, bool]] = {}
    for r in rows:
        sel = _sel_ids(r["selected"])
        for x in _cand_ids(r["candidates"]):
            verdict.setdefault((r["seed"], x), {})[r["who"]] = x in sel

    both = {k: v for k, v in verdict.items() if len(v) == 2}
    agree = [(k, next(iter(v.values()))) for k, v in both.items() if len(set(v.values())) == 1]
    union = [(k, any(v.values())) for k, v in both.items()]
    everyone = [(k, any(v.values())) for k, v in verdict.items()]

    print(f"\n{len(verdict)} judged pairs; {len(both)} judged by two labellers, "
          f"agreeing on {len(agree)}"
          + (f" ({len(agree) / len(both):.1%})" if both else ""))
    _score(agree, labels, "GOLD = both labellers agree (strictest)")
    _score(union, labels, "GOLD = either said same-story (recall-favouring)")
    _score(everyone, labels, "GOLD = every judged pair, any labeller")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--batch", default=None,
                    help="score a LIVE label batch by key instead of the committed gold")
    ap.add_argument("--agreed-only", dest="agreed_only", action="store_true",
                    help="drop the 36 adjudicated pairs; checks a result does not hinge on them")
    ap.add_argument("--as-of", dest="as_of", default=None,
                    help="rebuild the window as it stood on this date (YYYY-MM-DD)")
    ap.add_argument("--resolution", type=float, default=None)
    a = ap.parse_args()
    asyncio.run(main(a.batch, a.as_of, a.resolution, a.agreed_only))
