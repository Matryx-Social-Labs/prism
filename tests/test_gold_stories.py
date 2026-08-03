"""Invariants for the story-layer gold set. No database.

The gold set is the only thing that can tell a story-layer change from a
regression, so a mistake in the labels is worse than no labels: it would look
like evidence. These check the shape a hand-edited dict can plausibly break.
"""

import pytest

from tools.gold_stories import AMBIGUOUS, STORIES, STORY_OF, event_count, pairs, story_count


def test_no_event_is_in_two_stories():
    seen: dict[str, str] = {}
    for key, ids in STORIES.items():
        for e in ids:
            assert e not in seen, f"{e} is in both {seen.get(e)} and {key}"
            seen[e] = key
    assert len(seen) == event_count()


def test_ids_are_uuids_and_unique_within_a_story():
    for key, ids in STORIES.items():
        assert len(ids) == len(set(ids)), f"{key} lists an event twice"
        for e in ids:
            assert len(e) == 36 and e.count("-") == 4, f"{key}: {e!r} is not a uuid"


def test_ambiguous_names_a_real_pair_of_distinct_stories():
    """A typo here silently un-skips a pair, which then scores as a hard negative."""
    for fs in AMBIGUOUS:
        assert len(fs) == 2, f"{fs} is not a pair"
        for key in fs:
            assert key in STORIES, f"AMBIGUOUS names unknown story {key!r}"


def test_the_set_scores_both_directions():
    p = pairs()
    pos = sum(1 for v in p.values() if v)
    neg = len(p) - pos
    # Both failure directions must be representable or the set can't catch one.
    assert pos >= 20, f"only {pos} same-story pairs — cannot detect over-splitting"
    assert neg >= 100, f"only {neg} different-story pairs — cannot detect over-merging"


def test_ambiguous_pairs_are_actually_skipped():
    p = pairs()
    a = STORIES["cjp-police-force"][0]
    b = STORIES["wangchuk-hunger-strike"][0]
    assert (min(a, b), max(a, b)) not in p


def test_a_clearly_different_pair_is_kept_as_a_negative():
    """The counterpart: skipping must be surgical, not blanket. Wildfires in France
    and a Delhi protest are not a judgement call."""
    p = pairs()
    a = STORIES["european-wildfires"][0]
    b = STORIES["cjp-police-force"][0]
    assert p[(min(a, b), max(a, b))] is False


def test_the_true_labelling_scores_perfectly():
    """Guards the scorer contract: feeding back the gold answer must be flawless,
    or every measurement taken with it is off by an unknown constant."""
    p = pairs()
    tp = fp = fn = 0
    for (a, b), same in p.items():
        pred = STORY_OF[a] == STORY_OF[b]
        tp += pred and same
        fp += pred and not same
        fn += (not pred) and same
    assert (fp, fn) == (0, 0) and tp > 0


@pytest.mark.parametrize("key", ["cjp-police-force", "neet-paper-leak-bill"])
def test_multi_event_stories_stay_in_the_published_size_range(key):
    """Story Forest (CIKM 2017) measured mean 4.07 / median 3 / max 25 events per
    story over 261 human-rated stories. A gold cluster far outside that is a sign
    the labeller merged a topic, which is the very bug being measured."""
    assert 2 <= len(STORIES[key]) <= 25


def test_counts_are_what_was_labelled():
    assert event_count() == 49
    assert story_count() == 25
