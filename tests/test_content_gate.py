"""The L2.5 content gate: shared actors group events, shared content keeps them.

Measured against tools/gold_stories on the CJP slice: wrong merges 228 -> 130 at
zero recall cost. See the table in correlation/partition.py.
"""

from correlation.partition import (
    Node,
    _content_linked,
    _content_words,
    split_on_shared_content,
)


def n(eid: str, title: str) -> Node:
    return Node(id=eid, title=title, sector=None, regions=[], occurred_at=None, source_count=1)


# Verbatim from the production group the gate was built to fix: one Leiden
# community holding the protest story AND an unrelated air-crash report.
PROTEST = n("a", "Pellet guns, shock batons used against protesters in Delhi; police deny")
RAF = n("b", "RAF Fired Pellets On Protesters On Orders Of Delhi Cop, Shows Police Document")
INJURED = n("d", "CJP's 'Sansad Chalo': 2 protestors injured; 21-year-old on ventilator")
CRASH = n("c", "'Not an in-house probe': AAIB explains to SC why AI171 crash report is late")


def test_the_aftermath_stays_with_its_story():
    """Different actors, same event — the case raising the entity floor breaks."""
    assert _content_linked(PROTEST, RAF) is True


def test_an_unrelated_event_is_cut_from_the_community():
    assert _content_linked(PROTEST, CRASH) is False


def test_split_separates_them_and_keeps_the_story_whole():
    nodes = {x.id: x for x in (PROTEST, RAF, CRASH)}
    out = split_on_shared_content({"a": 0, "b": 0, "c": 0}, nodes)
    assert out["a"] == out["b"], "the protest story was split"
    assert out["c"] != out["a"], "the crash report stayed fused to the protest"


AISA = n("e", "AISA alleges crackdown on student protesters, seeks release of detained activists")
SC_RELEASE = n("f", "Supreme Court orders all states to release protesting students under 18")


def test_a_story_survives_on_a_chain_not_on_every_pair():
    """Three real headlines from one gold story. The first and last share NO word —
    "protesters" vs "protesting" — and are held together only by the middle one
    ("protesters" ... "release"). The gate is transitive, which is why the measured
    recall never moved. Without transitivity this would be a recall trade, not the
    free precision win the shipped threshold was chosen for."""
    assert _content_linked(PROTEST, SC_RELEASE) is False, "fixture no longer tests a chain"
    assert _content_linked(PROTEST, AISA) is True
    assert _content_linked(AISA, SC_RELEASE) is True
    nodes = {x.id: x for x in (PROTEST, AISA, SC_RELEASE)}
    out = split_on_shared_content({"a": 0, "e": 0, "f": 0}, nodes)
    assert out["a"] == out["f"], "no chain held the story together"


def test_morphology_is_a_known_ceiling_not_an_accident():
    """"protesters" vs "protestors" is a real miss. Documented rather than fixed:
    the transitive chain absorbs it, and a stemmer is only worth adding if recall
    starts moving. If someone adds stemming, this test should start failing."""
    assert _content_linked(PROTEST, INJURED) is False


def test_it_can_only_split_never_merge():
    """It refines a Leiden partition. If it could merge, it would undo boundaries
    Leiden and the LLM veto already agreed on."""
    same = n("d", "Pellet guns, shock batons used against protesters in Delhi; police deny")
    nodes = {x.id: x for x in (PROTEST, same)}
    out = split_on_shared_content({"a": 0, "d": 1}, nodes)  # already separate
    assert out["a"] != out["d"], "two communities were merged"


# --- absence of evidence must never split -----------------------------------
# The gold set behind the shipped threshold covers LATIN headlines only. A naive
# [a-z] tokeniser returns nothing for Devanagari, so every non-Latin story would
# shatter into singletons — and it would look like a clean split, not a bug.

HINDI_A = n("h1", "पैलेट गन, इलेक्ट्रिक बैटन और वकीलों पर हमला पुलिस पर SC के बड़े सवाल")
HINDI_B = n("h2", "दिल्ली में CJP प्रदर्शन के चलते 16 मेट्रो स्टेशन बंद, तीन इंटरचेंज")
KANNADA = n("k1", "ರಾಹುಲ್ ಸಭೆ ಅಂತ್ಯ, ಬೆಂಗಳೂರಿನತ್ತ ಡಿಕೆಶಿ")


def test_devanagari_headlines_are_tokenised_not_blanked():
    assert _content_words(HINDI_A.title), "Devanagari tokenised to nothing"
    assert _content_words(KANNADA.title), "Kannada tokenised to nothing"


def test_a_cross_script_pair_is_never_split():
    """An English and a Hindi headline about one story share zero literal words.
    The gate was never measured on that pair, so it must not act on it."""
    assert _content_linked(PROTEST, HINDI_A) is True
    assert _content_linked(HINDI_A, KANNADA) is True


def test_a_non_latin_community_is_not_shattered():
    nodes = {x.id: x for x in (HINDI_A, HINDI_B, KANNADA, PROTEST)}
    out = split_on_shared_content(dict.fromkeys(nodes, 0), nodes)
    assert len(set(out.values())) == 1, "a mixed-script community was split apart"


def test_an_untokenisable_title_keeps_its_link():
    """Punctuation-only or very short titles carry no evidence either way."""
    empty = n("e", "...")
    assert _content_linked(PROTEST, empty) is True


def test_stoplist_holds_function_words_not_news_words():
    """Stripping news vocabulary is what collapsed an early version to a 2% link
    rate: 'police' and 'court' are the story signal, not noise."""
    from correlation.partition import _TITLE_STOP

    for w in ("police", "court", "protest", "hospital", "bill", "students"):
        assert w not in _TITLE_STOP, f"{w!r} is story signal and must not be stopped"
    for w in ("about", "would", "their", "which"):
        assert w in _TITLE_STOP
