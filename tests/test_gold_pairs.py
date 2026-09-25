"""Integrity of the random-sample pair labels.

These guard the labels, not the clustering. This is the set any corpus-level claim
has to rest on, so a silent malformation here would propagate into every later
measurement as evidence.
"""

import uuid

from tools.gold_pairs import GOLD_PAIRS, pair_count, positive_count


def test_counts_match_what_was_labelled():
    assert pair_count() == 398
    # 61 until 2026-09-25: two positives paired the Thrissur leopard with a
    # Palakkad one and were corrected on re-reading (tools/gold_same_happening).
    assert positive_count() == 59


def test_keys_are_article_uuid_pairs():
    for a, b in GOLD_PAIRS:
        uuid.UUID(a)
        uuid.UUID(b)
        assert a != b, "an article cannot pair with itself"


def test_no_pair_is_labelled_twice_in_either_direction():
    """(a,b) and (b,a) are the same judgement. Two entries could disagree, and the
    scorer would silently count one pair twice."""
    seen = set()
    for a, b in GOLD_PAIRS:
        key = frozenset((a, b))
        assert key not in seen, f"duplicate pair {a} / {b}"
        seen.add(key)


def test_the_positive_rate_is_what_the_measurements_assumed():
    """14.8% positives (59 of 398; 61 before the 2026-09-25 correction). Every precision/recall figure in the module
    docstring is computed against this base rate; if the labels change, those
    numbers are stale and the docstring needs rewriting rather than this test
    relaxing to accommodate them."""
    rate = positive_count() / pair_count()
    assert 0.14 < rate < 0.17


def test_seeds_are_a_real_sample_not_a_handful():
    """The whole point of this set is that it is uniformly sampled. If it collapsed
    to a couple of seeds it would be as biased as the set it exists to correct."""
    seeds = {a for a, _ in GOLD_PAIRS}
    assert len(seeds) >= 55, "too few distinct seed articles to call this a sample"
