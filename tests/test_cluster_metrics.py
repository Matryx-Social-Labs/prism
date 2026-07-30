"""Hand-computed cases for the clustering scorer.

Every expected value below is worked out by hand in the docstring or comment, not
copied from a run of the code — a metric verified against its own output is a
metric that can be confidently wrong. These are the cases that would let a broken
scorer wave through the exact defect it exists to catch.
"""

import pytest

from correlation.cluster_metrics import b_cubed, detection_cost, macro_purity, score


def test_perfect_clustering_scores_one():
    labels = {"a": "1", "b": "1", "c": "2"}
    p, r, f = b_cubed(labels, labels)
    assert (p, r, f) == (1.0, 1.0, 1.0)
    assert macro_purity(labels, labels) == 1.0


def test_everything_in_one_cluster_is_perfect_recall_and_poor_precision():
    """The over-merger's signature. Gold has two events of 2; predicting one
    cluster of 4 gives every item recall 1.0 and precision 2/4."""
    gold = {"a": "1", "b": "1", "c": "2", "d": "2"}
    predicted = dict.fromkeys("abcd", "X")
    p, r, f = b_cubed(predicted, gold)
    assert r == 1.0
    assert p == 0.5
    assert f == pytest.approx(2 / 3)
    # Cluster-weighted: the single cluster is half one gold event, half the other.
    assert macro_purity(predicted, gold) == 0.5


def test_everything_apart_is_perfect_precision_and_poor_recall():
    """The fragmenter's signature — the mirror of the case above."""
    gold = {"a": "1", "b": "1", "c": "2", "d": "2"}
    predicted = {i: i for i in "abcd"}
    p, r, f = b_cubed(predicted, gold)
    assert p == 1.0
    assert r == 0.5
    # Purity cannot see fragmentation at all; that is what recall is for.
    assert macro_purity(predicted, gold) == 1.0


def test_b3_precision_is_the_over_merge_signal():
    """One contaminant in an otherwise clean 5-article event — the DMK/NEET shape.

    Predicted: {a,b,c,d,X} as one cluster. Gold: a-d are event 1, X is event 2.
    Each of a..d sees 4 of its 5 clustermates as correct -> precision 4/5.
    X sees 1 of 5 -> precision 1/5. Mean = (4*0.8 + 0.2)/5 = 0.68.
    """
    gold = {"a": "1", "b": "1", "c": "1", "d": "1", "X": "2"}
    predicted = dict.fromkeys(["a", "b", "c", "d", "X"], "E")
    p, r, f = b_cubed(predicted, gold)
    assert p == pytest.approx(0.68)
    assert r == 1.0
    assert macro_purity(predicted, gold) == pytest.approx(0.8)


def test_macro_purity_is_cluster_weighted_where_b3_is_item_weighted():
    """The reason both are reported. One big clean cluster plus four small fused
    ones: B-cubed F1 stays high because most ITEMS are in the clean cluster, while
    macro purity collapses because most CLUSTERS are broken."""
    gold, predicted = {}, {}
    for i in range(20):  # one clean 20-article event
        gold[f"big{i}"] = "G"
        predicted[f"big{i}"] = "P"
    for k in range(4):  # four 2-article clusters, each fusing two gold events
        gold[f"s{k}a"] = f"A{k}"
        gold[f"s{k}b"] = f"B{k}"
        predicted[f"s{k}a"] = predicted[f"s{k}b"] = f"S{k}"

    p, _, f = b_cubed(predicted, gold)
    mp = macro_purity(predicted, gold)
    assert p > 0.85, "B-cubed precision is dominated by the 20 clean items"
    assert mp == pytest.approx(0.6), "4 clusters at 0.5 and 1 at 1.0 -> 0.6"
    assert mp < p, "the cluster-weighted view must be harsher here — that is its job"


def test_only_items_in_both_labellings_are_scored():
    gold = {"a": "1", "b": "1"}
    predicted = {"a": "X", "b": "X", "ghost": "X"}
    s = score(predicted, gold)
    assert s.items == 2
    assert s.b3_f1 == 1.0


def test_score_reports_cluster_counts():
    """The integer that catches what the averages hide."""
    gold = {"a": "1", "b": "2", "c": "3", "d": "4"}
    predicted = {"a": "X", "b": "X", "c": "Y", "d": "Y"}
    s = score(predicted, gold)
    assert (s.predicted_clusters, s.gold_clusters) == (2, 4)


def test_empty_input_does_not_divide_by_zero():
    assert b_cubed({}, {}) == (0.0, 0.0, 0.0)
    assert macro_purity({}, {}) == 0.0
    assert score({}, {}).items == 0


def test_detection_cost_punishes_false_alarms_harder_than_misses():
    """The whole point of using Cdet instead of F1 here: a wrong merge costs more
    than a missed one. Same error COUNT, different cost."""
    balanced = dict(targets=100, non_targets=100)
    miss_heavy = detection_cost(misses=10, false_alarms=0, **balanced)
    fa_heavy = detection_cost(misses=0, false_alarms=10, **balanced)
    assert fa_heavy == pytest.approx(4 * miss_heavy)
    assert detection_cost(misses=0, false_alarms=0, **balanced) == 0.0


def test_detection_cost_needs_both_classes():
    with pytest.raises(ValueError):
        detection_cost(misses=0, false_alarms=0, targets=0, non_targets=10)
