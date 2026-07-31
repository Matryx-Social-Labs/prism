"""Evaluate candidate entity-match rules against the gold labels. Read-only.

    uv run python -m tools.tune_entity_rule

Builds every pair over the labelled articles, labels each pair same-event or not
from tools/gold_labels, and scores candidate rules by detection cost. This is the
fast loop: no database writes, no re-clustering, seconds per candidate.

WHAT THIS DOES NOT MODEL, so read results accordingly:

  - The EMBEDDING gate. Production also requires cosine distance <= 0.45 to the
    event centroid, and article embeddings are not stored (they are computed at
    match time and only the event keeps one). So neither production's row nor any
    candidate here carries that gate. Both sides are missing it equally, which
    makes the COMPARISON fair, but every absolute precision here is pessimistic.
  - The CASCADE. find_event tries URL, then title, then embedding, then entities.
    The entity path only ever sees what the earlier paths missed, so its recall in
    production is not this recall.
  - GREEDY assignment. find_event takes the first matching event, not the best
    over all pairs. Pairwise precision is an upper bound on what clustering does
    with the same rule.

The comparison is like-for-like and that is the point; the absolute numbers are
not a quality claim.
"""

from __future__ import annotations

import itertools
import json
import math
from datetime import datetime

FEATURES = "/tmp/pairs_features.json"  # written by the exporter in the PR description


def load(path: str = FEATURES) -> tuple[list[dict], dict[str, int], int]:
    d = json.load(open(path))
    return d["articles"], d["df"], d["n_articles"]


def build_pairs(articles: list[dict], df: dict[str, int], n_articles: int) -> list[dict]:
    """Every pair, with the features each candidate rule needs."""

    def log_idf(slug: str) -> float:
        # Kumaran & Allan's form. 1/df, which production uses, is far more
        # aggressive and hands the whole score to the single rarest shared actor.
        return math.log((n_articles + 1) / (df.get(slug, 0) + 0.5))

    out = []
    for x, y in itertools.combinations(articles, 2):
        ex, ey = set(x["ents"]), set(y["ents"])
        shared = ex & ey
        inv = [1.0 / df[s] for s in shared if s in df]
        norm_x = math.sqrt(sum(log_idf(s) ** 2 for s in ex))
        norm_y = math.sqrt(sum(log_idf(s) ** 2 for s in ey))
        out.append(
            {
                "same": x["gold"] == y["gold"],
                "n_shared": len(shared),
                "hours": abs(
                    (datetime.fromisoformat(x["ts"]) - datetime.fromisoformat(y["ts"])).total_seconds()
                )
                / 3600.0,
                "sum_inv_df": sum(inv),
                "max_inv_df": max(inv) if inv else 0.0,
                # The replacement for max(1/df): agreement across the WHOLE cast,
                # so one coincidentally-rare shared actor cannot carry a merge.
                "ent_cos": (
                    sum(log_idf(s) ** 2 for s in shared) / (norm_x * norm_y)
                    if shared and norm_x and norm_y
                    else 0.0
                ),
            }
        )
    return out


def evaluate(pairs: list[dict], rule) -> dict:
    pos = [p for p in pairs if p["same"]]
    neg = [p for p in pairs if not p["same"]]
    tp = sum(1 for p in pos if rule(p))
    fp = sum(1 for p in neg if rule(p))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / len(pos) if pos else 0.0
    prior = len(pos) / len(pairs)
    cdet = ((len(pos) - tp) / len(pos)) * prior + 4.0 * (fp / len(neg)) * (1 - prior)
    return {"cdet": cdet, "precision": precision, "recall": recall, "false_merges": fp}


def PRODUCTION(p: dict) -> bool:
    """correlation/clustering.py::_match_by_entities as it stands, including its
    own 4-day window so the comparison below is like-for-like."""
    return (
        p["n_shared"] >= 2
        and p["sum_inv_df"] >= 0.15
        and (p["max_inv_df"] >= 0.1 or p["n_shared"] >= 4)
        and p["hours"] <= 96
    )


def CANDIDATE(p: dict) -> bool:
    """Measured 2026-07-30: strictly dominates production — precision +28%,
    recall +83%, wrong merges -41%, Cdet -19%. Not a trade-off, a win on every
    axis.

    The load-bearing change is ent_cos replacing max(1/df). A max rule over rare
    features merges on the single rarest shared actor, so one coincidence — an
    obscure activist group, one NER error — carries the whole decision. A cosine
    over the full log-IDF entity vector requires the casts to broadly agree.
    """
    return p["ent_cos"] >= 0.45 and p["n_shared"] >= 2 and p["hours"] <= 48


def main() -> None:
    articles, df, n = load()
    pairs = build_pairs(articles, df, n)
    pos = sum(1 for p in pairs if p["same"])
    print(f"{len(pairs)} pairs  same-event={pos}  different={len(pairs) - pos}\n")

    rules = [
        ("PRODUCTION (incl. its 96h window)", PRODUCTION),
        (
            "production without the #108 broad-shared branch",
            lambda p: p["n_shared"] >= 2 and p["sum_inv_df"] >= 0.15 and p["max_inv_df"] >= 0.1 and p["hours"] <= 96,
        ),
        ("CANDIDATE ent_cos>=0.45, n>=2, <=48h", CANDIDATE),
        ("  ...at 0.50 (higher precision, less recall)", lambda p: p["ent_cos"] >= 0.50 and p["n_shared"] >= 2 and p["hours"] <= 48),
        ("  ...at 0.45 with production's 96h window", lambda p: p["ent_cos"] >= 0.45 and p["n_shared"] >= 2 and p["hours"] <= 96),
    ]
    print(f"{'rule':48} {'Cdet':>7} {'P':>6} {'R':>6} {'wrong':>6}")
    print("-" * 78)
    for name, rule in rules:
        r = evaluate(pairs, rule)
        print(f"{name:48} {r['cdet']:7.4f} {r['precision']:6.3f} {r['recall']:6.3f} {r['false_merges']:6d}")

    b, c = evaluate(pairs, PRODUCTION), evaluate(pairs, CANDIDATE)
    print("\ncandidate vs production, like for like:")
    for k, fmt in (("precision", "{:.3f}"), ("recall", "{:.3f}"), ("false_merges", "{:d}"), ("cdet", "{:.4f}")):
        pct = (c[k] / b[k] - 1) * 100 if b[k] else float("nan")
        print(f"  {k:13} {fmt.format(b[k])} -> {fmt.format(c[k])}   ({pct:+.0f}%)")


if __name__ == "__main__":
    main()
