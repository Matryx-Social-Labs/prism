"""The cross-language headline tier ranks by IDF word-cosine and is off until set."""

from correlation.clustering import headline_best
from tools.title_cosine import build_idf

ROWS = [
    ("a", "India rejects Pakistan-China Boundary Joint Commission"),
    ("b", "Foundation stone laid for Mahadeshwara Swamy temple"),
    ("c", "Supreme Court expresses shock over deaths in relief camps in Manipur"),
]


def test_the_nearest_prism_headline_wins_and_the_score_is_the_cosine():
    idf = build_idf([t for _, t in ROWS] + ["India rejects China-Pakistan Boundary Joint Commission"])
    best, score = headline_best("India rejects China-Pakistan Boundary Joint Commission", ROWS, idf)
    assert best == "a" and score > 0.9
    best, score = headline_best("Supreme Court expresses concern over deaths in Manipur relief camps", ROWS, idf)
    assert best == "c" and 0.5 < score < 1.0


def test_nothing_alike_scores_nothing():
    idf = build_idf([t for _, t in ROWS])
    best, score = headline_best("Camel trapped on railway tracks rescued by loco pilot", ROWS, idf)
    assert score < 0.2


def test_the_tier_is_off_by_default():
    from common.config import get_settings

    assert get_settings().prism_headline_tier_threshold == 0.0
