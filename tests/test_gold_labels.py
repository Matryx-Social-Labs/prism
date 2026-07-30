"""Integrity of the hand-labelled gold set.

These guard the labels themselves, not the clustering. A gold set that is
silently malformed is worse than none: every later measurement inherits the fault
and reads as evidence.
"""

from correlation.cluster_metrics import score
from tools.gold_labels import GOLD, gold_event_count, labelled_article_count


def test_indices_are_contiguous_from_zero():
    """Labels are POSITIONAL — index i is the i'th article by published_at. A hole
    means every later index in that event points at the wrong article."""
    for event, labels in GOLD.items():
        assert set(labels) == set(range(len(labels))), f"{event} has non-contiguous indices"


def test_counts_match_what_was_labelled():
    assert labelled_article_count() == 171
    assert gold_event_count() == 56


def test_labels_are_slugs():
    for event, labels in GOLD.items():
        for i, label in labels.items():
            assert label == label.strip().lower(), f"{event}[{i}] is not normalised"
            assert " " not in label, f"{event}[{i}] has a space"


def test_some_gold_events_span_predicted_clusters():
    """The set has to contain fragmentation as well as fusion, or B-cubed recall
    is structurally 1.0 and the scorer can be fooled by a change that splits
    everything into singletons."""
    where = {}
    for event, labels in GOLD.items():
        for label in labels.values():
            where.setdefault(label, set()).add(event)
    spanning = {k for k, v in where.items() if len(v) > 1}
    assert spanning, "no gold event spans two predicted clusters — recall signal is dead"
    # The three known ones, so a careless re-label can't quietly drop them.
    assert {"courts-police-action", "kangana-row", "kharge-shah"} <= spanning


def test_the_labelled_slice_is_genuinely_over_merged():
    """The premise of the whole exercise: on this slice, predicted clusters are far
    fewer than real events. If this ever inverts, the set has been mislabelled or
    the clustering changed radically and the labels need revisiting."""
    predicted, gold = {}, {}
    for event, labels in GOLD.items():
        for i, label in labels.items():
            key = f"{event}:{i}"
            predicted[key] = event
            gold[key] = label
    s = score(predicted, gold)
    assert s.predicted_clusters == 6
    assert s.gold_clusters == 56
    # Precision is the over-merge signal and it should be dire here by design.
    assert s.b3_precision < 0.35
    assert s.b3_recall > 0.9
