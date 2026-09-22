"""Where does the tree actually put a story, and is it right?

Runs live production titles through the subject cascade and prints the
distribution per branch, the confidence at which each placement was made, and a
sample to read. Nothing here scores itself: a taxonomy has no ground truth
until a person reads the placements, so this prints what a person needs to read
and `--sample N` gives them a numbered list to mark up.

    uv run python -m tools.bakeoff_subject --n 400            # distribution + cost
    uv run python -m tools.bakeoff_subject --n 400 --sample 40  # a list to read
    uv run python -m tools.bakeoff_subject --n 400 --was other  # only today's "other"

Reads production (read-only). ~$0.00012 an item: 400 items is five cents.
The question it exists to answer BEFORE anything reclassifies: does the tree
empty the `other` bucket into places that are actually right, and does any node
fall below the ~30-stories-a-month floor that would make it a promise the
product cannot keep.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter
from pathlib import Path

import asyncpg

from classification import subject as subj
from classification.decide import state_for
from common import subjects
from common.decisions import decide
from tools.snapshot_l2 import _prod_url

OUT = Path(".cache/bakeoff_subject.json")
CONCURRENCY = 8
SAMPLE_SEED = 0.29


async def sample(n: int, was: str | None) -> list[dict]:
    c = await asyncpg.connect(_prod_url(), timeout=180)
    try:
        await c.execute("SET default_transaction_read_only = on")
        await c.execute("SELECT setseed($1)", SAMPLE_SEED)
        where = "sector = $2" if was and was != "other" else (
            "(sector = 'other' OR sector IS NULL)" if was else "TRUE"
        )
        args = [n] + ([was] if was and was != "other" else [])
        return [dict(r) for r in await c.fetch(
            f"""
            SELECT id::text AS id, title, summary, sector, subsector
            FROM events
            WHERE {where}
              AND COALESCE(jsonb_array_length(projection->'source_slugs'), 0) > 0
              AND last_updated_at > now() - interval '30 days'
            ORDER BY random() LIMIT $1
            """, *args)]
    finally:
        await c.close()


async def place(rows: list[dict]) -> list[dict]:
    """One call for root + every level-2 menu; a second only where the tree
    goes deeper and the story landed there."""
    sem = asyncio.Semaphore(CONCURRENCY)
    questions = {"subject": subj.root_question(), **subj.level_two_questions()}

    async def one(r: dict) -> dict:
        state = state_for(r["title"], r.get("summary"))
        async with sem:
            try:
                answers = await decide(state, questions, trace_name="subject")
            except Exception as exc:  # noqa: BLE001 — a failed item is a row in the table
                return {**r, "error": f"{type(exc).__name__}: {str(exc)[:110]}"}
            path, confidence = subj.path_from(answers)
            cost = answers.usage.cost
            if subj.needs_third_level(path):
                try:
                    deeper = await decide(state, subj.level_three_question(path), trace_name="subject-leaf")
                    path, confidence = subj.deepen(path, confidence, deeper)
                    cost += deeper.usage.cost
                except Exception:  # noqa: BLE001 — stay at the parent, which is a valid place
                    pass
        return {**r, "path": path, "confidence": round(confidence, 3), "cost": cost}

    return await asyncio.gather(*(one(r) for r in rows))


def report(rows: list[dict], sample_n: int) -> dict:
    placed = [r for r in rows if "path" in r]
    errors = [r for r in rows if "error" in r]
    by_path = Counter(r["path"] for r in placed)
    by_root = Counter(r["path"].split(".")[0] for r in placed)
    cost = sum(r.get("cost", 0.0) for r in placed)

    print(f"\nplaced {len(placed)} of {len(rows)}  ({len(errors)} failed)   ${cost:.4f}")
    print(f"\n{'root':16} {'n':>5}  share")
    for root, n in by_root.most_common():
        print(f"  {subjects.get(root).label if subjects.get(root) else root:14} {n:5d}  {100 * n / max(len(placed), 1):5.1f}%")

    print(f"\n{'path':34} {'n':>5}  {'depth':>5}  median conf")
    for path, n in by_path.most_common():
        confs = sorted(r["confidence"] for r in placed if r["path"] == path)
        print(f"  {path:32} {n:5d}  {subjects.depth(path):5d}  {confs[len(confs) // 2]:.2f}")

    # A node nobody reaches is a promise the product cannot keep. The sample is
    # 30 days, so the floor is read directly off the share.
    total_month = 9984  # events in the live 30-day window, 2026-09-22
    print("\nprojected stories a month (the ~30 floor):")
    thin = [(p, n) for p, n in by_path.items() if n / max(len(placed), 1) * total_month < 30]
    for path, n in sorted(thin, key=lambda kv: kv[1]):
        print(f"  THIN  {path:32} ~{n / max(len(placed), 1) * total_month:5.0f}/month")
    if not thin:
        print("  every node clears it")

    if sample_n:
        print(f"\n─── {sample_n} placements to read ───")
        for i, r in enumerate(placed[:sample_n], 1):
            was = f"{r['sector']}/{r['subsector']}" if r.get("subsector") else (r.get("sector") or "none")
            print(f"{i:3d}. [{r['confidence']:.2f}] {r['path']}")
            print(f"     was {was} :: {r['title'][:88]}")

    return {"by_path": dict(by_path), "by_root": dict(by_root), "cost_usd": cost,
            "placed": len(placed), "errors": len(errors)}


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--sample", type=int, default=0, help="print this many placements to read")
    ap.add_argument("--was", help="only events whose current sector is this ('other' for the unclassified)")
    args = ap.parse_args()

    rows = await sample(args.n, args.was)
    print(f"sampled {len(rows)} events", file=sys.stderr)
    placed = await place(rows)
    summary = report(placed, args.sample)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps({"summary": summary, "rows": placed}, indent=1, default=str))
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
