"""Jev's typed answers become the same GateResult/ClassificationResult the LLM
pair produces, so nothing downstream knows which answered."""

import pytest

from classification import decide as d
from classification.decide import QUESTIONS, decided_confidence, to_results
from common.decisions import ChoiceAnswer, Decisions, NoulAnswer
from common.regions import IN_STATES
from common.taxonomy import TAXONOMY


def _answers(**over):
    base = {
        "event": NoulAnswer(noul=0.9),
        "not_news": NoulAnswer(noul=0.05),
        "sector": ChoiceAnswer(choice="politics", confidence=0.97, probabilities={}),
        "subsector": ChoiceAnswer(choice="politics/courts_law", confidence=0.8, probabilities={}),
        "indian_state": ChoiceAnswer(choice="IN-KA", confidence=1.0, probabilities={}),
        "country": ChoiceAnswer(choice="IN", confidence=1.0, probabilities={}),
        "language": ChoiceAnswer(choice="kn", confidence=1.0, probabilities={}),
        "cyber": NoulAnswer(noul=0.02),
        "markets": NoulAnswer(noul=0.1),
        "fast_lane": NoulAnswer(noul=0.3),
    }
    return Decisions(answers={**base, **over})


def test_the_question_set_is_derived_from_the_taxonomy_and_the_state_table():
    assert set(QUESTIONS["sector"].criteria) == set(TAXONOMY)
    subs = {f"{s}/{sub}" for s, subs in TAXONOMY.items() for sub in subs}
    assert set(QUESTIONS["subsector"].criteria) == subs | {"none"}
    assert set(QUESTIONS["indian_state"].criteria) == {c for c, _ in IN_STATES} | {"national", "none"}
    assert {"IN", "US", "other"} <= set(QUESTIONS["country"].criteria)


def test_a_kannada_state_court_story_maps_to_the_llm_shape():
    gate, cls = to_results(_answers(), source_country="IN")
    assert gate.is_relevant
    assert (cls.sector, cls.subsector, cls.language) == ("politics", "courts_law", "kn")
    assert cls.regions == ["IN", "IN-KA"]
    assert cls.role_interests == [] and cls.route == "standard"
    assert cls.confidence == pytest.approx(0.97)


def test_a_subsector_under_another_sector_is_dropped_not_stored():
    _, cls = to_results(_answers(subsector=ChoiceAnswer(choice="finance/markets", confidence=0.9, probabilities={})), source_country="IN")
    assert cls.subsector is None


def test_national_scope_carries_no_state_and_other_country_falls_back_to_the_source():
    _, cls = to_results(
        _answers(indian_state=ChoiceAnswer(choice="national", confidence=1, probabilities={}),
                 country=ChoiceAnswer(choice="other", confidence=0.6, probabilities={})),
        source_country="IN",
    )
    assert cls.regions == ["IN"]
    _, cls = to_results(
        _answers(indian_state=ChoiceAnswer(choice="none", confidence=1, probabilities={}),
                 country=ChoiceAnswer(choice="other", confidence=0.6, probabilities={})),
        source_country=None,
    )
    assert cls.regions == []


def test_lens_and_route_nouls_cross_at_their_measured_floors():
    _, cls = to_results(_answers(cyber=NoulAnswer(noul=0.7), markets=NoulAnswer(noul=0.5), fast_lane=NoulAnswer(noul=0.7)), source_country="IN")
    assert cls.role_interests == ["cyber", "markets"] and cls.route == "fast_lane"
    _, cls = to_results(_answers(cyber=NoulAnswer(noul=0.69), markets=NoulAnswer(noul=0.49), fast_lane=NoulAnswer(noul=0.69)), source_country="IN")
    assert cls.role_interests == [] and cls.route == "standard"


@pytest.mark.parametrize("event,not_news,expected", [(0.9, 0.05, True), (0.29, 0.05, False), (0.9, 0.4, False), (0.3, 0.39, True)])
def test_the_gate_needs_an_event_and_not_a_column(event, not_news, expected):
    gate, cls = to_results(_answers(event=NoulAnswer(noul=event), not_news=NoulAnswer(noul=not_news)), source_country="IN")
    assert gate.is_relevant is expected
    assert (cls is not None) is expected
    assert "event=" in gate.reason


def test_confidence_is_the_sector_when_kept_and_the_not_news_margin_when_rejected():
    assert decided_confidence(_answers()) == pytest.approx(0.97)
    assert decided_confidence(_answers(sector=ChoiceAnswer(choice="other", confidence=0.4, probabilities={}))) == pytest.approx(0.4)
    assert decided_confidence(_answers(not_news=NoulAnswer(noul=0.9))) == pytest.approx(0.9)
    assert decided_confidence(_answers(event=NoulAnswer(noul=0.1), not_news=NoulAnswer(noul=0.2))) == pytest.approx(0.9)


def test_the_state_is_the_prompt_body_the_llm_saw():
    state = d.state_for("Title", "x" * 5000)
    assert state["title"] == "Title" and len(state["content"]) == d.MAX_GATE_CHARS
    assert d.state_for("T", None)["content"] == "(no content — title only)"
