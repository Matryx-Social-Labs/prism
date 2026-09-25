"""Place existing stories on the subject tree.

A tree that only applies to stories published after it shipped leaves every
archive page and every subject-scoped analysis half empty. Placing all of them
costs about $1.30 at the measured $0.00009 an event (tools/bakeoff_subject).

    uv run python -m tools.backfill_subjects --limit 50          # a dry run, prints placements
    uv run python -m tools.backfill_subjects --limit 500 --apply
    uv run python -m tools.backfill_subjects --apply             # everything unplaced

WRITES TO PRODUCTION when --apply is given, and to nothing otherwise. Only ever
sets `subject_path`/`subject_confidence`, only on rows where the path is NULL,
so it is safe to re-run and cannot undo a later reclassification. `sector` and
`subsector` are NOT rewritten: they are what the old classifier said, they are
still what old readers read, and quietly changing them under a reader is a
different decision from adding a path.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from collections import Counter

import asyncpg

from classification.decide import state_for
from classification.subject import (
    deepen,
    level_three_question,
    level_two_questions,
    needs_third_level,
    path_from,
    root_question,
)
from common.decisions import decide
from common.logging import get_logger
from tools.snapshot_l2 import _prod_url

logger = get_logger(__name__)
CONCURRENCY = 8
BATCH = 200


async def fetch_unplaced(c: asyncpg.Connection, limit: int) -> list[dict]:
    return [dict(r) for r in await c.fetch(
        """
        SELECT id::text AS id, title, summary FROM events
        WHERE subject_path IS NULL
          AND COALESCE(jsonb_array_length(projection->'source_slugs'), 0) > 0
        ORDER BY last_updated_at DESC
        LIMIT $1
        """, limit)]


async def place(rows: list[dict]) -> list[dict]:
    sem = asyncio.Semaphore(CONCURRENCY)
    questions = {"subject": root_question(), **level_two_questions()}

    async def one(r: dict) -> dict:
        state = state_for(r["title"], r.get("summary"))
        async with sem:
            try:
                answers = await decide(state, questions, trace_name="backfill-subject")
            except Exception as exc:  # noqa: BLE001 — an unplaced row stays unplaced and is retried next run
                logger.warning("backfill_place_failed", event_id=r["id"], error=str(exc)[:140])
                return {**r, "path": None}
            path, confidence = path_from(answers)
            cost = answers.usage.cost
            if path and needs_third_level(path):
                try:
                    deeper = await decide(state, level_three_question(path), trace_name="backfill-subject-leaf")
                    path, confidence = deepen(path, confidence, deeper)
                    cost += deeper.usage.cost
                except Exception:  # noqa: BLE001 — the parent is a valid place
                    pass
        return {**r, "path": path, "confidence": confidence, "cost": cost}

    return await asyncio.gather(*(one(r) for r in rows))


async def write(c: asyncpg.Connection, placed: list[dict]) -> int:
    rows = [(r["id"], r["path"], float(r["confidence"])) for r in placed if r.get("path")]
    if not rows:
        return 0
    # Only where it is still NULL: a story reclassified since this batch was
    # read keeps the newer answer.
    await c.executemany(
        """
        UPDATE events SET subject_path = $2, subject_confidence = $3
        WHERE id = $1::uuid AND subject_path IS NULL
        """, rows)
    return len(rows)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--limit", type=int, default=0, help="stop after this many events (0 = all unplaced)")
    ap.add_argument("--apply", action="store_true", help="write; without it nothing is written")
    args = ap.parse_args()

    c = await asyncpg.connect(_prod_url(), timeout=180)
    if not args.apply:
        await c.execute("SET default_transaction_read_only = on")
    try:
        total, cost, by_path = 0, 0.0, Counter()
        while True:
            take = BATCH if not args.limit else min(BATCH, args.limit - total)
            if take <= 0:
                break
            rows = await fetch_unplaced(c, take)
            if not rows:
                break
            placed = await place(rows)
            cost += sum(r.get("cost", 0.0) for r in placed)
            by_path.update(r["path"] for r in placed if r.get("path"))
            written = await write(c, placed) if args.apply else 0
            total += len(rows)
            print(f"  {total:6d} placed   ${cost:.4f}   {'wrote ' + str(written) if args.apply else 'DRY RUN'}", flush=True)
            if not args.apply:
                for r in placed[:20]:
                    print(f"      {r['path'] or '(unplaced)':30} {r['title'][:74]}")
                break  # a dry run shows one batch and stops
        print(f"\n{'wrote' if args.apply else 'would place'} {total} events, ${cost:.4f}")
        for path, n in by_path.most_common(15):
            print(f"  {path:32} {n}")
        return 0
    finally:
        await c.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
