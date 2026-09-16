"""The canonical title is Prism's headline when there is one, labelled as ours."""

from correlation.consumer import canonical_title


def test_prism_headline_becomes_the_title_and_is_marked():
    assert canonical_title({"headline": "  Cabinet expansion delayed again  "}, "outlet words") == ("Cabinet expansion delayed again", "prism")


def test_without_a_headline_the_outlet_words_stay_unmarked():
    assert canonical_title({}, "outlet words") == ("outlet words", None)
    assert canonical_title({"headline": "   "}, "outlet words") == ("outlet words", None)
