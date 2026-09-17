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


def test_the_set_spans_more_than_one_topic():
    """The first pass was all CJP politics, which is too narrow to select a
    hyperparameter on — a CPM sweep cross-validated over it produced a config that
    LOST to production on held-out stories in both directions. Sport, business and
    civic infrastructure are in here so a protest-specific rule cannot look general."""
    for key in ("sri-lanka-test-squad", "tn-ford-return", "best-bus-crash-probe",
                "karnataka-cabinet-expansion"):
        assert key in STORIES


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
    assert event_count() == 86
    assert story_count() == 45


# --- the scorer itself -------------------------------------------------------
# tools/score_stories.score_pairs is now the single scorer for both the live
# report and the offline sweep. If it drifts, every story-layer number drifts
# with it silently, so pin its contract.


def test_perfect_prediction_scores_perfectly():
    from tools.score_stories import score_pairs

    s = score_pairs(dict(STORY_OF))
    assert s["P"] == 1.0 and s["R"] == 1.0 and s["fp"] == 0 and s["fn"] == 0


def test_putting_everything_in_one_group_is_all_recall_no_precision():
    from tools.score_stories import score_pairs

    s = score_pairs(dict.fromkeys(STORY_OF, "one"))
    assert s["R"] == 1.0 and s["fn"] == 0
    assert s["fp"] > 0 and s["P"] < 0.5


def test_all_singletons_is_all_precision_no_recall():
    from tools.score_stories import score_pairs

    s = score_pairs({e: e for e in STORY_OF})
    assert s["fp"] == 0 and s["R"] == 0.0 and s["fn"] > 0


def test_key_restriction_scores_only_the_named_stories():
    """The cross-validation split depends on this: a config tuned on one fold must
    be judged only on pairs from the other, or held-out numbers are meaningless."""
    from tools.score_stories import score_pairs

    subset = {"european-wildfires", "cjp-police-force"}
    s = score_pairs(dict(STORY_OF), subset)
    full = score_pairs(dict(STORY_OF))
    assert 0 < s["pairs"] < full["pairs"]
    # Cross-fold pairs must be excluded, not merely down-weighted.
    inside = sum(len(STORIES[k]) for k in subset)
    assert s["pairs"] <= inside * (inside - 1) // 2


def test_coverage_gate_rejects_a_plausible_score_from_a_stale_join():
    """The live partition once found 2/86 gold events and still printed P/R/F1.
    Those numbers described the join failure, not the story layer."""
    from tools.score_stories import require_coverage

    with pytest.raises(SystemExit, match=r"INVALID SCORE.*2/86"):
        require_coverage(2, 86, what="labelled events")


def test_coverage_gate_accepts_the_documented_ninety_percent_floor():
    from tools.score_stories import require_coverage

    assert require_coverage(90, 100, what="labelled events") == pytest.approx(0.9)
