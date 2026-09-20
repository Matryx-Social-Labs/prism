"""The gate for podcast clips: is this clip about THIS story?

    uv run python -m tools.gold_clips --sample 60      # label pairs, interactively
    uv run python -m tools.gold_clips --report         # precision by threshold

Labels: y = about this event · t = about the topic, not this event · n = unrelated
· s = skip. Appended to tools/gold_clips.jsonl with the score the matcher gave,
so --report can sweep PRISM_CLIP_MIN_COS without re-matching. Ships at ≥ 0.9
precision on "y" among what the threshold keeps; below that the section does
not exist (absence of a clip is never a signal either way).
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

GOLD = pathlib.Path(__file__).with_name("gold_clips.jsonl")

SAMPLE = """
SELECT ec.event_id, ec.window_id, ec.score, ec.entity_hits, ec.start_s, ec.end_s,
       ev.title, ev.projection->'lens_briefs'->>'reader' AS brief,
       w.text, e.title AS episode, s.name AS show, e.published_at
FROM event_clips ec
JOIN events ev ON ev.id = ec.event_id
JOIN podcast_windows w ON w.id = ec.window_id
JOIN podcast_episodes e ON e.id = w.episode_id
JOIN podcast_shows s ON s.slug = e.show_slug
"""


def _load() -> list[dict]:
    if not GOLD.exists():
        return []
    return [json.loads(line) for line in GOLD.read_text().splitlines() if line.strip()]


async def sample(n: int) -> int:
    done = {(g["event_id"], g["window_id"]) for g in _load()}
    async with get_session_factory()() as s:
        rows = (await s.execute(text(SAMPLE))).mappings().all()
    rows = [r for r in rows if (str(r["event_id"]), str(r["window_id"])) not in done]
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
            print(f"\n[{i}/{len(picked)}]  score {r['score']:.3f} · cast hits {r['entity_hits']} · {r['show']} · {r['episode'][:60]}")
            print(f"  STORY: {r['title']}\n         {brief[:160]}")
            print(f"  CLIP {r['start_s']:.0f}–{r['end_s']:.0f}s: {r['text'][:600]}")
            while True:
                a = input("  y / t / n / s > ").strip().lower()
                if a in {"y", "t", "n", "s", "q"}:
                    break
            if a == "q":
                break
            if a == "s":
                continue
            f.write(json.dumps({"event_id": str(r["event_id"]), "window_id": str(r["window_id"]), "score": float(r["score"]),
                                "entity_hits": int(r["entity_hits"]), "label": a, "title": r["title"], "show": r["show"]}) + "\n")
            f.flush()
            labelled += 1
    return labelled


def report() -> int:
    gold = _load()
    if not gold:
        print("no labels yet — run --sample first")
        return 1
    print(f"{len(gold)} labelled · y={sum(g['label'] == 'y' for g in gold)} t={sum(g['label'] == 't' for g in gold)} n={sum(g['label'] == 'n' for g in gold)}")
    print("threshold  kept  precision(y)  recall(y)")
    total_y = sum(g["label"] == "y" for g in gold) or 1
    for t in [0.80, 0.82, 0.84, 0.86, 0.88, 0.90, 0.92]:
        kept = [g for g in gold if g["score"] >= t]
        y = sum(g["label"] == "y" for g in kept)
        p = y / len(kept) if kept else 0.0
        flag = " ← ships" if p >= 0.9 and kept else ""
        print(f"  {t:.2f}     {len(kept):4d}   {p:.3f}         {y / total_y:.3f}{flag}")
    return 0


async def live() -> int:
    """Precision among labelled pairs the CURRENT event_clips still contains:
    how the matcher's filters (not just the threshold) fare on the gold."""
    gold = _load()
    if not gold:
        print("no labels yet")
        return 1
    # A merged clip is keyed by its best window, which moves as the filters
    # change; a gold pair survives if the event still has a clip from the same
    # episode overlapping the labelled window's stretch.
    async with get_session_factory()() as s:
        clips = (await s.execute(text(
            "SELECT ec.event_id, w.episode_id, ec.start_s, ec.end_s FROM event_clips ec JOIN podcast_windows w ON w.id = ec.window_id"
        ))).all()
        wins = {str(r[0]): (str(r[1]), float(r[2]), float(r[3])) for r in (await s.execute(text(
            "SELECT id, episode_id, start_s, end_s FROM podcast_windows WHERE id = ANY(CAST(:ids AS uuid[]))"
        ), {"ids": [g["window_id"] for g in gold]})).all()}
        n_events = (await s.execute(text("SELECT count(DISTINCT event_id) FROM event_clips"))).scalar()
        n_clips = len(clips)
    by_event: dict[str, list] = {}
    for ev, ep, a, b in clips:
        by_event.setdefault(str(ev), []).append((str(ep), float(a), float(b)))

    def alive(g: dict) -> bool:
        w = wins.get(g["window_id"])
        if not w:
            return False
        return any(ep == w[0] and a < w[2] and b > w[1] for ep, a, b in by_event.get(g["event_id"], []))

    survivors = [g for g in gold if alive(g)]
    dropped = [g for g in gold if not alive(g)]
    y = sum(g["label"] == "y" for g in survivors)
    print(f"live: {n_clips} clips on {n_events} events · gold survivors {len(survivors)}/{len(gold)} · precision(y) {y / len(survivors) if survivors else 0:.3f} · y lost {sum(g['label'] == 'y' for g in dropped)}")
    for g in survivors:
        if g["label"] != "y":
            print(f"   still in ({g['label']}): {g['score']:.3f} {g['title'][:70]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int, default=0)
    ap.add_argument("--report", action="store_true")
    ap.add_argument("--live", action="store_true", help="precision among gold pairs the current event_clips keeps")
    args = ap.parse_args()
    if args.live:
        return asyncio.run(live())
    if args.sample:
        n = asyncio.run(sample(args.sample))
        print(f"labelled {n}")
    if args.report or not args.sample:
        return report()
    return 0


if __name__ == "__main__":
    sys.exit(main())
