"""The gate for X posts: is this post about THIS story?

    uv run python -m tools.gold_xposts --sample 50     # label pairs, interactively
    uv run python -m tools.gold_xposts --report        # precision by threshold and by method
    uv run python -m tools.gold_xposts --live          # precision among gold pairs still attached

Labels: y = about this event · t = about the topic, not this event · n = unrelated
· s = skip. Appended to tools/gold_xposts.jsonl with the score and method the
matcher gave. Ships at ≥ 0.9 precision on "y" among what the threshold keeps;
below that the API stays off and the section does not exist.
"""
from __future__ import annotations

import argparse
import asyncio
import json
import pathlib
import random
import sys

from sqlalchemy import text

from common.db import get_session_factory

GOLD = pathlib.Path(__file__).with_name("gold_xposts.jsonl")

SAMPLE = """
SELECT ep.event_id, ep.post_id, ep.score, ep.method,
       ev.title, ev.projection->'lens_briefs'->>'reader' AS brief,
       p.text, p.created_at, a.handle, a.name
FROM event_x_posts ep
JOIN events ev ON ev.id = ep.event_id
JOIN x_posts p ON p.post_id = ep.post_id
JOIN x_accounts a ON a.handle = p.handle
WHERE p.deleted_at IS NULL
"""


def _load() -> list[dict]:
    if not GOLD.exists():
        return []
    return [json.loads(line) for line in GOLD.read_text().splitlines() if line.strip()]


async def sample(n: int) -> int:
    done = {(g["event_id"], g["post_id"]) for g in _load()}
    async with get_session_factory()() as s:
        rows = (await s.execute(text(SAMPLE))).mappings().all()
    rows = [r for r in rows if (str(r["event_id"]), r["post_id"]) not in done]
    random.shuffle(rows)
    # Stratify: half from the band just above the floor, where the decision is.
    rows.sort(key=lambda r: r["score"])
    low, high = rows[: len(rows) // 2], rows[len(rows) // 2 :]
    picked = (low[: n // 2] + high[: n - n // 2])
    random.shuffle(picked)
    labelled = 0
    with GOLD.open("a") as f:
        for i, r in enumerate(picked, 1):
            brief = (r["brief"] or "").split(". ")[0]
            print(f"\n[{i}/{len(picked)}]  score {r['score']:.3f} · {r['method']} · @{r['handle']} · {r['created_at']:%d %b %H:%M}")
            print(f"  STORY: {r['title']}\n         {brief[:160]}")
            print(f"  POST: {r['text'][:600]}")
            while True:
                a = input("  y / t / n / s > ").strip().lower()
                if a in {"y", "t", "n", "s", "q"}:
                    break
            if a == "q":
                break
            if a == "s":
                continue
            f.write(json.dumps({"event_id": str(r["event_id"]), "post_id": r["post_id"], "score": float(r["score"]),
                                "method": r["method"], "label": a, "title": r["title"], "handle": r["handle"]}) + "\n")
            f.flush()
            labelled += 1
    return labelled


def report() -> int:
    gold = _load()
    if not gold:
        print("no labels yet — run --sample first")
        return 1
    print(f"{len(gold)} labelled · y={sum(g['label'] == 'y' for g in gold)} t={sum(g['label'] == 't' for g in gold)} n={sum(g['label'] == 'n' for g in gold)}")
    for method in ("url", "judge"):
        rows = [g for g in gold if g["method"] == method]
        if rows:
            print(f"  {method}: {len(rows)} labelled · precision(y) {sum(g['label'] == 'y' for g in rows) / len(rows):.3f}")
    judged = [g for g in gold if g["method"] == "judge"]
    print("threshold (judge tier)  kept  precision(y)  recall(y)")
    total_y = sum(g["label"] == "y" for g in judged) or 1
    for t in [0.80, 0.82, 0.84, 0.86, 0.88, 0.90, 0.92]:
        kept = [g for g in judged if g["score"] >= t]
        y = sum(g["label"] == "y" for g in kept)
        p = y / len(kept) if kept else 0.0
        flag = " ← ships" if p >= 0.9 and kept else ""
        print(f"  {t:.2f}                  {len(kept):4d}   {p:.3f}         {y / total_y:.3f}{flag}")
    return 0


async def live() -> int:
    """Precision among labelled pairs the CURRENT event_x_posts still contains."""
    gold = _load()
    if not gold:
        print("no labels yet")
        return 1
    async with get_session_factory()() as s:
        pairs = {(str(r[0]), r[1]) for r in (await s.execute(text("SELECT event_id, post_id FROM event_x_posts"))).all()}
        n_events = (await s.execute(text("SELECT count(DISTINCT event_id) FROM event_x_posts"))).scalar()
    survivors = [g for g in gold if (g["event_id"], g["post_id"]) in pairs]
    dropped = [g for g in gold if (g["event_id"], g["post_id"]) not in pairs]
    y = sum(g["label"] == "y" for g in survivors)
    print(f"live: {len(pairs)} posts on {n_events} events · gold survivors {len(survivors)}/{len(gold)} · precision(y) {y / len(survivors) if survivors else 0:.3f} · y lost {sum(g['label'] == 'y' for g in dropped)}")
    for g in survivors:
        if g["label"] != "y":
            print(f"   still in ({g['label']}): {g['score']:.3f} {g['method']} @{g['handle']} {g['title'][:70]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--live", action="store_true", help="precision among gold pairs the current event_x_posts keeps")
    args = ap.parse_args()
    if args.live:
        return asyncio.run(live())
    if args.report:
        return report()
    if args.sample:
        n = asyncio.run(sample(args.sample))
        print(f"\n{n} labelled → {GOLD}")
        return report() if n else 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
