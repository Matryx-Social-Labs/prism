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
MIN_COVERAGE = 0.90


def require_coverage(found: int, total: int, *, what: str,
                     minimum: float = MIN_COVERAGE) -> float:
    """Refuse to turn a stale/partial join into a plausible quality score."""
    coverage = found / total if total else 0.0
    if coverage < minimum:
        raise SystemExit(
            f"INVALID SCORE: only {found}/{total} {what} covered "
            f"({coverage:.1%}; need >= {minimum:.0%}). Rebuild with the gold "
            "set's --as-of date or refresh the labels."
        )
    return coverage


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


def score_pairs(predicted: dict[str, str], keys: set[str] | None = None) -> dict:
    """THE scorer. One copy, so two callers cannot quietly disagree about what a
    number means — tools/sweep_partition imports this rather than reimplementing it.

    `keys` restricts scoring to events in those gold stories, which is how the
    cross-validation split judges a config on stories it was not tuned on.
    """
    tp = fp = fn = tn = 0
    for (a, b), same in pairs().items():
        if a not in predicted or b not in predicted:
            continue
        if keys is not None and not (STORY_OF[a] in keys and STORY_OF[b] in keys):
            continue
        together = predicted[a] == predicted[b]
        tp += together and same
        fp += together and not same
        fn += (not together) and same
        tn += (not together) and not same
    prec = tp / (tp + fp) if tp + fp else 0.0
    rec = tp / (tp + fn) if tp + fn else 0.0
    npos, nneg = tp + fn, fp + tn
    return {
        "P": prec, "R": rec,
        "F1": 2 * prec * rec / (prec + rec) if prec + rec else 0.0,
        "Cdet": (C_MISS * fn / npos if npos else 0) + (C_FA * fp / nneg if nneg else 0),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn, "pairs": tp + fp + fn + tn,
    }


def report(predicted: dict[str, str], label: str = "current partition") -> None:
    """predicted: event_id -> whatever group id the system put it in."""
    s = score_pairs(predicted)
    prec, rec, f1, cdet = s["P"], s["R"], s["F1"], s["Cdet"]
    tp, fp, fn = s["tp"], s["fp"], s["fn"]
    scored = {"n": s["pairs"]}

    covered = len([e for e in STORY_OF if e in predicted])
    print(f"\n── {label} ──")
    print(f"  {covered}/{event_count()} labelled events found, {scored['n']} pairs scored")
    require_coverage(covered, event_count(), what="labelled events")
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
