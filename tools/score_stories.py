"""Score the CURRENT partition's story boundaries against tools/gold_stories. Read-only.

    uv run python -m tools.score_stories

Pairwise precision/recall over the labelled slice, plus the two structural numbers
that pairwise scores hide: how many gold stories got split, and how many distinct
gold stories each predicted group swallowed.

READ THE NUMBERS CORRECTLY.

  - PRECISION is over-merging: of the pairs we put together, how many belong
    together. This is the defect the CJP slice was chosen for.
  - RECALL is over-splitting.
  - Cdet weights a false alarm 4x a miss, the TDT convention, because a wrong
    merge is visible to a reader (two stories fused on one card) while a miss is
    only a duplicate card. Same weighting tools/gold_pairs uses at layer 1.

And the standing warning from tools/gold_pairs, which cost a reverted PR to learn:
PAIRWISE SCORES OVER-PREDICT THE BENEFIT OF TIGHTENING. Scoring pairs is stateless,
so it cannot see that removing one edge cascades into a component splitting three
ways. A change that looks good here must still be replayed before it ships.
"""

from __future__ import annotations

import asyncio
import os
import re
import subprocess

import asyncpg

from tools.gold_stories import STORIES, STORY_OF, event_count, pairs, story_count

C_MISS, C_FA = 1.0, 4.0


def _db_url() -> str:
    raw = os.environ.get("REPAIR_DATABASE_URL")
    if not raw:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=90,
        ).stdout
        for line in out.splitlines():
            if line.startswith("DATABASE_URL="):
                raw = line.split("=", 1)[1].strip()
                break
    if not raw:
        raise SystemExit("no database url (set REPAIR_DATABASE_URL)")
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw)


def report(predicted: dict[str, str], label: str = "current partition") -> None:
    """predicted: event_id -> whatever group id the system put it in."""
    p = pairs()
    scored = {k: v for k, v in p.items() if k[0] in predicted and k[1] in predicted}
    tp = fp = fn = tn = 0
    for (a, b), same in scored.items():
        together = predicted[a] == predicted[b]
        tp += together and same
        fp += together and not same
        fn += (not together) and same
        tn += (not together) and not same
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    npos, nneg = tp + fn, fp + tn
    cdet = (C_MISS * fn / npos if npos else 0) + (C_FA * fp / nneg if nneg else 0)

    covered = len([e for e in STORY_OF if e in predicted])
    print(f"\n── {label} ──")
    print(f"  {covered}/{event_count()} labelled events found, {len(scored)} pairs scored")
    print(f"  P {prec:.4f}   R {rec:.4f}   F1 {f1:.4f}   Cdet {cdet:.4f}")
    print(f"  tp {tp}  fp {fp} (wrong merges)  fn {fn} (wrong splits)")

    # Structural view — what pairwise numbers hide.
    split = 0
    for ids in STORIES.values():
        groups = {predicted[e] for e in ids if e in predicted}
        if len(groups) > 1:
            split += 1
    by_group: dict[str, set[str]] = {}
    for e, g in predicted.items():
        if e in STORY_OF:
            by_group.setdefault(g, set()).add(STORY_OF[e])
    fused = {g: ks for g, ks in by_group.items() if len(ks) > 1}
    print(f"  gold stories split across >1 group: {split}/{story_count()}")
    print(f"  groups holding >1 gold story: {len(fused)}")
    for g, ks in sorted(fused.items(), key=lambda kv: -len(kv[1]))[:6]:
        print(f"    group {str(g)[:8]:10} swallowed {len(ks):2}: {', '.join(sorted(ks)[:5])}")


async def main() -> None:
    c = await asyncpg.connect(_db_url(), timeout=60)
    try:
        await c.execute("SET default_transaction_read_only = on")
        run = await c.fetchval("SELECT id::text FROM partition_runs WHERE status='current'")
        rows = await c.fetch(
            "SELECT event_id::text e, story_label::text g FROM event_story "
            "WHERE run_id=$1::uuid AND event_id = ANY($2::uuid[])",
            run, list(STORY_OF),
        )
    finally:
        await c.close()
    report({r["e"]: r["g"] for r in rows}, f"partition run {run[:8]}")


if __name__ == "__main__":
    asyncio.run(main())
