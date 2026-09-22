"""The subject tree and the cascade that places a story on it."""

import pytest

from classification import subject as subj
from classification.decide import QUESTIONS, to_results
from common import subjects
from common.decisions import ChoiceAnswer, Decisions, NoulAnswer
from common.taxonomy import TAXONOMY

# ── the tree ────────────────────────────────────────────────────────────────


def test_the_tree_is_well_formed_and_every_node_bridges_to_the_old_columns():
    subjects.demo()  # parents exist, criteria present, legacy maps into TAXONOMY


def test_a_node_without_its_own_sector_inherits_one():
    # civic.crime.violent declares no legacy pair; it must still answer.
    assert subjects.legacy_for("civic.crime.violent") == ("other", None)
    assert subjects.legacy_for("education.exams") == ("other", None)
    assert subjects.legacy_for("tech.security.malware") == ("cybersecurity", "malware_threats")


def test_every_legacy_pair_is_one_the_old_taxonomy_knows():
    for s in subjects.SUBJECTS:
        sector, sub = subjects.legacy_for(s.path)
        assert sector in TAXONOMY
        assert sub is None or sub in TAXONOMY[sector]


def test_the_roots_are_the_nav_and_nothing_else_is_depth_one():
    assert [s.path for s in subjects.children(None)] == list(subjects.ROOTS)
    assert all(subjects.depth(p) == 1 for p in subjects.ROOTS)
    assert "civic" in subjects.ROOTS and "education" in subjects.ROOTS


def test_descendants_is_the_prefix_query_the_node_pages_use():
    under_crime = {s.path for s in subjects.descendants("civic.crime")}
    assert under_crime == {
        "civic.crime.violent", "civic.crime.property",
        "civic.crime.sexual", "civic.crime.policing",
    }
    assert "civic.crime" not in under_crime, "descendants excludes the node itself"
    assert subjects.descendants("civic.crime.violent") == ()


# ── the cascade ─────────────────────────────────────────────────────────────


def _answers(root: str, root_conf: float = 0.9, child: str | None = None, child_conf: float = 0.9) -> Decisions:
    answers: dict = {"subject": ChoiceAnswer(choice=root, confidence=root_conf, probabilities={})}
    if child is not None:
        answers[f"sub_{root}"] = ChoiceAnswer(choice=child, confidence=child_conf, probabilities={})
    return Decisions(answers=answers)


def test_a_confident_placement_descends():
    path, conf = subj.path_from(_answers("civic", 0.95, "crime", 0.9))
    assert path == "civic.crime"
    assert conf == pytest.approx(0.9), "the path is only as sure as its least sure step"


def test_an_unsure_child_leaves_the_story_on_its_root():
    """A parent is a valid resting place (founder, 2026-09-22): `civic` is true
    about a story we could not place, where a guessed leaf would not be."""
    path, _ = subj.path_from(_answers("civic", 0.95, "crime", subj.DESCEND_MIN_CONFIDENCE - 0.01))
    assert path == "civic"


def test_choosing_general_stays_at_the_parent():
    path, _ = subj.path_from(_answers("sports", 0.9, subj.STAY, 0.99))
    assert path == "sports"


def test_an_invented_child_does_not_become_a_path():
    path, _ = subj.path_from(_answers("sports", 0.9, "quidditch", 0.99))
    assert path == "sports"


def test_an_answer_off_the_menu_gives_no_path_rather_than_a_guess():
    """An unplaced story is visible and fixable; one filed under the wrong root
    is neither."""
    assert subj.path_from(_answers("nonsense", 0.9))[0] is None
    assert subj.path_from(Decisions(answers={}))[0] is None


def test_only_the_two_deep_branches_ask_a_third_question():
    deep = [s.path for s in subjects.SUBJECTS if subj.needs_third_level(s.path) and subjects.depth(s.path) == 2]
    assert set(deep) == {"tech.security", "civic.crime"}
    assert not subj.needs_third_level("sports.cricket")


def test_the_third_call_deepens_only_when_it_is_sure():
    sure = Decisions(answers={"leaf": ChoiceAnswer(choice="violent", confidence=0.99, probabilities={})})
    assert subj.deepen("civic.crime", sure)[0] == "civic.crime.violent"
    unsure = Decisions(answers={"leaf": ChoiceAnswer(choice="violent", confidence=0.2, probabilities={})})
    assert subj.deepen("civic.crime", unsure)[0] == "civic.crime"
    stay = Decisions(answers={"leaf": ChoiceAnswer(choice=subj.STAY, confidence=0.99, probabilities={})})
    assert subj.deepen("civic.crime", stay)[0] == "civic.crime"


def test_every_menu_is_short_enough_to_be_read_carefully():
    subj.demo()


# ── the questions ride in the call that already runs ────────────────────────


def test_the_subject_questions_are_in_the_gate_classify_call():
    """One parallel pass: the root and every level-2 menu cost input tokens and
    no extra round trip."""
    assert "subject" in QUESTIONS
    for root in subjects.ROOTS:
        assert f"sub_{root}" in QUESTIONS


def _full(**over) -> Decisions:
    base = {
        "event": NoulAnswer(noul=0.9), "not_news": NoulAnswer(noul=0.05),
        "sector": ChoiceAnswer(choice="politics", confidence=0.9, probabilities={}),
        "subsector": ChoiceAnswer(choice="politics/courts_law", confidence=0.9, probabilities={}),
        "indian_state": ChoiceAnswer(choice="none", confidence=1, probabilities={}),
        "country": ChoiceAnswer(choice="IN", confidence=1, probabilities={}),
        "language": ChoiceAnswer(choice="en", confidence=1, probabilities={}),
        "cyber": NoulAnswer(noul=0.0), "markets": NoulAnswer(noul=0.0), "fast_lane": NoulAnswer(noul=0.0),
        "subject": ChoiceAnswer(choice="civic", confidence=0.95, probabilities={}),
        "sub_civic": ChoiceAnswer(choice="accidents", confidence=0.92, probabilities={}),
    }
    return Decisions(answers={**base, **over})


def test_the_classification_carries_the_path_and_keeps_the_old_columns():
    _, cls = to_results(_full(), source_country="IN")
    assert cls.subject_path == "civic.accidents"
    assert cls.subject_confidence == pytest.approx(0.92)
    # The old columns still answer, for every reader that has not moved.
    assert cls.sector == "politics" and cls.subsector == "courts_law"


# ── the node pages ──────────────────────────────────────────────────────────


async def _db_reachable() -> bool:
    from sqlalchemy import text as _text
    from sqlalchemy.exc import SQLAlchemyError

    from common.db import session_scope

    try:
        async with session_scope() as s:
            await s.execute(_text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _get(path: str):
    from httpx import ASGITransport, AsyncClient

    from api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.get(path)


async def test_a_node_counts_exactly_what_it_lists():
    """The page said "0 stories" above two stories, because the count carried a
    30-day window the list did not. The two must describe the same set."""
    if not await _db_reachable():
        pytest.skip("no database")
    import uuid as _uuid
    from datetime import UTC, datetime, timedelta

    from common.db import session_scope
    from common.models import Event

    old = datetime.now(UTC) - timedelta(days=200)
    async with session_scope() as s:
        for i in range(3):
            s.add(Event(id=_uuid.uuid4(), title=f"old crime {i}", sector="other",
                        subject_path="civic.crime.violent", last_updated_at=old,
                        projection={"source_slugs": ["the_hindu"]}))
    body = (await _get("/api/v1/subject/civic/crime?limit=60")).json()
    assert body["story_count"] >= 3
    assert body["story_count"] == len(body["stories"]) or len(body["stories"]) == 60


async def test_a_node_holds_everything_under_it():
    if not await _db_reachable():
        pytest.skip("no database")
    body = (await _get("/api/v1/subject/civic")).json()
    assert body["node"]["path"] == "civic"
    assert [a["path"] for a in body["ancestors"]] == []
    assert {c["slug"] for c in body["children"]} >= {"crime", "accidents", "community"}
    deep = (await _get("/api/v1/subject/civic/crime/violent")).json()
    assert [a["path"] for a in deep["ancestors"]] == ["civic", "civic.crime"]


async def test_an_unknown_path_is_404():
    if not await _db_reachable():
        pytest.skip("no database")
    assert (await _get("/api/v1/subject/not/a/subject")).status_code == 404


async def test_the_tree_endpoint_rolls_counts_up_to_every_ancestor():
    if not await _db_reachable():
        pytest.skip("no database")
    tree = (await _get("/api/v1/subjects")).json()
    assert [r["slug"] for r in tree["roots"]] == list(subjects.ROOTS)
    by_path = {n["path"]: n for n in tree["nodes"]}
    assert by_path["civic"]["story_count"] >= by_path["civic.crime"]["story_count"]
