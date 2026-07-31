"""Integrity of the hand-labelled gold set.

These guard the labels themselves, not the clustering. A gold set that is silently
malformed is worse than none: every later measurement inherits the fault and reads
as evidence.
"""

import uuid

from correlation.cluster_metrics import score
from tools.gold_labels import GOLD, gold_event_count, labelled_article_count


def test_counts_match_what_was_labelled():
    assert labelled_article_count() == 171
    assert gold_event_count() == 56


def test_keys_are_article_uuids():
    """Keyed by ARTICLE ID, not by position. The first version indexed labels by
    publication order within a predicted event, so the moment a repair moved
    articles between events every index pointed at the wrong article — which is
    exactly what happened the first time a repair ran."""
    for key in GOLD:
        uuid.UUID(key)  # raises if this is a position or an event prefix


def test_labels_are_slugs():
    for aid, label in GOLD.items():
        assert label == label.strip().lower(), f"{aid} label is not normalised"
        assert " " not in label, f"{aid} label has a space"


def test_no_label_is_a_singleton_by_accident():
    """27 of the 56 real events are genuinely single-article. That is a fact about
    the corpus worth pinning: if a careless re-label collapses them, recall stops
    meaning anything."""
    counts: dict[str, int] = {}
    for label in GOLD.values():
        counts[label] = counts.get(label, 0) + 1
    assert sum(1 for n in counts.values() if n == 1) == 27
    assert max(counts.values()) == 20


def test_a_perfect_clustering_of_these_labels_scores_one():
    """Sanity on the pairing of labels and scorer: clustering exactly by gold label
    must score 1.0. If this ever fails, the labels and the metric disagree about
    what a cluster is."""
    predicted = dict(GOLD)
    s = score(predicted, GOLD)
    assert s.b3_precision == 1.0
    assert s.b3_recall == 1.0
    assert s.macro_purity == 1.0
    assert s.predicted_clusters == s.gold_clusters == 56


def test_the_all_in_one_cluster_case_is_dire():
    """The other end: fusing everything must score badly on precision while recall
    stays perfect. This is the shape production was in before the 0.0.81.10 repair."""
    predicted = dict.fromkeys(GOLD, "one-big-blob")
    s = score(predicted, GOLD)
    assert s.b3_recall == 1.0
    assert s.b3_precision < 0.15
    assert s.predicted_clusters == 1
