"""The adjudicated gold sets hold the shape the scorers assume.

Data modules, so the risk is a hand edit that quietly breaks a scorer's filter:
a provenance string that is neither "agree" nor "adj:..." would make
`pairs(include_adjudicated=False)` silently keep a disputed pair, and the
"does this hinge on adjudication?" check would stop checking anything.
"""

from tools import gold_claims, gold_story_pairs


def test_story_pairs_provenance_is_closed():
    for (a, b), (same, prov) in gold_story_pairs.PAIRS.items():
        assert a != b
        assert isinstance(same, bool)
        assert prov == "agree" or prov.startswith("adj:"), (a, b, prov)


def test_agreed_only_drops_exactly_the_adjudicated_pairs():
    all_ = gold_story_pairs.pairs()
    agreed = gold_story_pairs.pairs(include_adjudicated=False)
    adjudicated = {k for k, (_, p) in gold_story_pairs.PAIRS.items() if p.startswith("adj:")}
    assert set(all_) - set(agreed) == adjudicated
    assert len(adjudicated) == 36, "the sheet had 36 disputed pairs"


def test_headline_numbers_match_the_adjudication():
    assert gold_story_pairs.positives() == 42
    assert len(gold_claims.CLAIMS) == 59
    assert round(gold_claims.precision(), 3) == 0.983
