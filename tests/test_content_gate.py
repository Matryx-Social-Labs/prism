"""The content gate: shared actors propose an edge, shared content confirms it.

Two independent gates (Story Forest's coarse+fine, CIKM 2017). This replaced a
post-hoc "split each community on shared headline words" pass, which measured as a
no-op at every floor below 0.30 — a big community stays chained together through
overlapping headlines, so transitivity defeats splitting after the fact. Gating the
EDGE instead, before Leiden ever sees it, is what actually worked:

    rb  1.0   floor 0.50 gate     P 0.2709  R 0.5340  F1 0.3595  Cdet 0.6496  fp 148
    cpm 0.020 floor 0.30 csim .20 P 0.4344  R 0.5146  F1 0.4711  Cdet 0.5710  fp  69
"""

from correlation.partition import (
    CONTENT_MIN_SIM,
    Node,
    _content_words,
    content_similarity,
    filter_edges_on_content,
)


def n(eid: str, title: str) -> Node:
    return Node(id=eid, title=title, sector=None, regions=[], occurred_at=None, source_count=1)


# Verbatim from the production group this was built to fix: one community holding
# the protest story AND an unrelated air-crash report.
PROTEST = n("a", "Pellet guns, shock batons used against protesters in Delhi; police deny")
RAF = n("b", "RAF Fired Pellets On Protesters On Orders Of Delhi Cop, Shows Police Document")
CRASH = n("c", "'Not an in-house probe': AAIB explains to SC why AI171 crash report is late")


def test_two_developments_of_one_story_are_similar():
    assert content_similarity(PROTEST, RAF) >= CONTENT_MIN_SIM


def test_an_unrelated_event_is_not():
    assert content_similarity(PROTEST, CRASH) < CONTENT_MIN_SIM


def test_the_unrelated_edge_is_dropped_and_the_real_one_kept():
    nodes = {x.id: x for x in (PROTEST, RAF, CRASH)}
    edges = [("a", "b", 0.9), ("a", "c", 0.9)]
    kept = filter_edges_on_content(edges, nodes)
    assert ("a", "b", 0.9) in kept, "a real story edge was cut"
    assert ("a", "c", 0.9) not in kept, "the crash report stayed linked to the protest"


def test_the_gate_only_removes_edges():
    """It filters a proposal list. If it could add, it would invent links no shared
    actor ever supported."""
    nodes = {x.id: x for x in (PROTEST, RAF, CRASH)}
    edges = [("a", "b", 0.9)]
    assert len(filter_edges_on_content(edges, nodes)) <= len(edges)


# --- absence of evidence must never cut --------------------------------------
# The gold set behind CONTENT_MIN_SIM is Latin-headline heavy. A naive [a-z]
# tokeniser returns nothing for Devanagari, so every non-Latin edge would be cut
# and it would look like a clean, decisive result rather than a bug.

HINDI_A = n("h1", "पैलेट गन, इलेक्ट्रिक बैटन और वकीलों पर हमला पुलिस पर SC के बड़े सवाल")
HINDI_B = n("h2", "दिल्ली में CJP प्रदर्शन के चलते 16 मेट्रो स्टेशन बंद, तीन इंटरचेंज")
KANNADA = n("k1", "ರಾಹುಲ್ ಸಭೆ ಅಂತ್ಯ, ಬೆಂಗಳೂರಿನತ್ತ ಡಿಕೆಶಿ")


def test_devanagari_and_kannada_are_tokenised_not_blanked():
    assert _content_words(HINDI_A.title), "Devanagari tokenised to nothing"
    assert _content_words(KANNADA.title), "Kannada tokenised to nothing"


def test_cross_script_is_no_evidence_not_dissimilar():
    """None, never 0.0 — an English and a Hindi headline about one story share no
    literal words, and this gate was never measured on that pair."""
    assert content_similarity(PROTEST, HINDI_A) is None
    assert content_similarity(HINDI_A, KANNADA) is None


def test_an_untokenisable_title_is_no_evidence():
    assert content_similarity(PROTEST, n("e", "...")) is None


def test_no_evidence_edges_survive_the_filter():
    """The whole failure mode in one assertion: if None were treated as 0.0, every
    cross-script edge would vanish here."""
    nodes = {x.id: x for x in (PROTEST, HINDI_A, KANNADA)}
    edges = [("a", "h1", 0.9), ("h1", "k1", 0.9)]
    assert filter_edges_on_content(edges, nodes) == edges


def test_an_edge_to_an_unknown_node_is_kept():
    """Never silently drop an edge because a node is missing from the map."""
    assert filter_edges_on_content([("a", "ghost", 0.9)], {"a": PROTEST}) == [("a", "ghost", 0.9)]


def test_similarity_is_symmetric():
    assert content_similarity(PROTEST, RAF) == content_similarity(RAF, PROTEST)


def test_stoplist_holds_function_words_not_news_words():
    """Stripping news vocabulary collapsed an early version to a 2% link rate:
    'police' and 'court' are the story signal, not noise."""
    from correlation.partition import _TITLE_STOP

    for w in ("police", "court", "protest", "hospital", "bill", "students"):
        assert w not in _TITLE_STOP, f"{w!r} is story signal and must not be stopped"
    for w in ("about", "would", "their", "which"):
        assert w in _TITLE_STOP
