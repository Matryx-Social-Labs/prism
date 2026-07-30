"""Scoring a clustering against a gold standard.

Every threshold in correlation/clustering.py was picked by reading clusters and
forming a judgement. That got the catastrophic failures (one event with 139
unrelated articles) but it cannot see the subtle ones, and it has already cost one
revert: ENTITY_MATCH_MIN_TOP_IDF shipped in 0.0.80.0 and had to be walked back in
0.0.80.5 because it rejected a real story. This module is so the next change is
argued against a number.

WHICH NUMBERS, and why these:

- B-cubed is the primary. Amigó et al. 2009 define four formal constraints a
  clustering metric should satisfy (homogeneity, completeness, rag bag, cluster
  size vs quantity) and show B-cubed is the only common metric satisfying all four.

- Report B-cubed PRECISION separately, not just F1. Precision is the over-merge
  signal: it falls exactly when one predicted cluster mixes several gold events,
  which is this product's failure mode. F1 averages that away against recall.

- MUC is deliberately absent. It is link-based and over-rewards merging — on the
  standard benchmark two systems 7.4 CEAF-e points apart score 99.30 and 98.88 on
  MUC. A metric that cannot separate an over-merger from a good system is worse
  than no metric, because it reads as success.

- Cluster COUNT against gold, as a plain integer. B-cubed is item-weighted, so it
  penalises mistakes on large clusters heavily and lets mistakes on small ones
  through; the count is the cheapest check on fragmentation and fusion, and on the
  published benchmark it separated systems that B-cubed did not.

ponytail: macro_purity stands in for CEAF-e, which needs an optimal one-to-one
cluster alignment (Hungarian) and so a scipy dependency this project does not
carry. Both are cluster-weighted rather than item-weighted, which is the property
that matters here — it stops a handful of huge clusters from dominating the score.
macro_purity is a strictly easier metric (greedy best-overlap per cluster, no
one-to-one constraint), so it OVERSTATES quality: two predicted clusters may both
claim the same gold event and both score well. Read it as a lower bound on the
damage, never as CEAF-e. Upgrade path: add scipy and use
scipy.optimize.linear_sum_assignment over the phi_4 matrix.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass


def _by_cluster(labels: dict[str, str]) -> dict[str, set[str]]:
    out: dict[str, set[str]] = defaultdict(set)
    for item, cluster in labels.items():
        out[cluster].add(item)
    return dict(out)


def _f1(p: float, r: float) -> float:
    return 0.0 if p + r == 0 else 2 * p * r / (p + r)


@dataclass(frozen=True)
class Scores:
    b3_precision: float
    b3_recall: float
    b3_f1: float
    macro_purity: float
    predicted_clusters: int
    gold_clusters: int
    items: int

    def __str__(self) -> str:
        return (
            f"B3 P={self.b3_precision:.4f} R={self.b3_recall:.4f} F1={self.b3_f1:.4f}  "
            f"macro_purity={self.macro_purity:.4f}  "
            f"clusters={self.predicted_clusters} (gold {self.gold_clusters})  n={self.items}"
        )


def b_cubed(predicted: dict[str, str], gold: dict[str, str]) -> tuple[float, float, float]:
    """B-cubed precision, recall, F1 over items present in BOTH labellings.

    Per item i with predicted cluster C(i) and gold cluster G(i):
        precision(i) = |C(i) & G(i)| / |C(i)|
        recall(i)    = |C(i) & G(i)| / |G(i)|
    and each is averaged over items. An item alone in both scores 1.0 on both.
    """
    items = predicted.keys() & gold.keys()
    if not items:
        return 0.0, 0.0, 0.0
    pred_c = _by_cluster({i: predicted[i] for i in items})
    gold_c = _by_cluster({i: gold[i] for i in items})

    p_sum = r_sum = 0.0
    for i in items:
        c = pred_c[predicted[i]]
        g = gold_c[gold[i]]
        shared = len(c & g)
        p_sum += shared / len(c)
        r_sum += shared / len(g)
    n = len(items)
    p, r = p_sum / n, r_sum / n
    return p, r, _f1(p, r)


def macro_purity(predicted: dict[str, str], gold: dict[str, str]) -> float:
    """Mean over PREDICTED clusters of (largest gold overlap / cluster size).

    Cluster-weighted, so a 2-article cluster counts as much as a 50-article one —
    which is the point. B-cubed is item-weighted and will happily hide a dozen
    small fused clusters behind one large clean one.

    1.0 means every predicted cluster is drawn from a single gold event. A cluster
    that fuses two equal-sized gold events scores 0.5. See the module docstring for
    why this is a lower bound on damage rather than CEAF-e.
    """
    items = predicted.keys() & gold.keys()
    if not items:
        return 0.0
    pred_c = _by_cluster({i: predicted[i] for i in items})
    total = 0.0
    for members in pred_c.values():
        counts: dict[str, int] = defaultdict(int)
        for i in members:
            counts[gold[i]] += 1
        total += max(counts.values()) / len(members)
    return total / len(pred_c)


def score(predicted: dict[str, str], gold: dict[str, str]) -> Scores:
    """Score a predicted clustering against gold. Both map item id -> cluster id."""
    items = predicted.keys() & gold.keys()
    p, r, f = b_cubed(predicted, gold)
    return Scores(
        b3_precision=p,
        b3_recall=r,
        b3_f1=f,
        macro_purity=macro_purity(predicted, gold),
        predicted_clusters=len({predicted[i] for i in items}),
        gold_clusters=len({gold[i] for i in items}),
        items=len(items),
    )


def detection_cost(
    misses: int,
    false_alarms: int,
    targets: int,
    non_targets: int,
    *,
    c_miss: float = 1.0,
    c_fa: float = 4.0,
) -> float:
    """TDT-style detection cost. Lower is better.

        Cdet = c_miss * P(miss) * P(target) + c_fa * P(FA) * P(non-target)

    Use this to pick a threshold instead of maximising F1, because F1 assumes the
    two errors cost the same and here they do not. An event that absorbs an
    unrelated story is a visible defect a reader will not forgive; two events that
    should have been one is a mild annoyance they may never notice. c_fa defaults
    to 4x c_miss to say so out loud — change it deliberately, not by accident.
    """
    if targets == 0 or non_targets == 0:
        raise ValueError("need both targets and non-targets to compute a cost")
    p_miss = misses / targets
    p_fa = false_alarms / non_targets
    prior = targets / (targets + non_targets)
    return c_miss * p_miss * prior + c_fa * p_fa * (1 - prior)
