"""Mode `confirm`: the fuzzy tiers propose, Jev decides every attach.

Measured 2026-09-29 against Jev's own same-happening test, 781 production
attaches since 09-24: the verified tier 100%, title 92%, embedding 76%,
entity_overlap 44% (28% clearly different). entity_overlap carried 19% of every
attach and 56% of the records shown as covered by two or more outlets. A
follow-up it swept in (a hunger strike into the student's death, a Supreme Court
ruling into the High Court's) now founds its own record, linked as a later
development of the first.

Jev is mocked; the contract under test is who gets asked, what each answer
does, and that a Jev failure keeps the old tiers' answer rather than turning
every retelling into a duplicate record.
"""

import uuid

import pytest
from sqlalchemy import text

import correlation.clustering as clustering
import correlation.consumer as consumer
import correlation.verify as verify
from common.config import get_settings
from common.db import session_scope
from common.decisions import Decisions, NoulAnswer
from tests.test_verified_tier import (
    FLOOR,
    _at,
    _db_reachable,
    _direction,
    _event_with_member,
    _incoming_article,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")

BLOCK = "Published now by x.\nHeadline: h\nSummary: s"


@pytest.fixture
def jev(monkeypatch):
    """Answers (same happening, later development) per event title; records the questions asked."""
    asked: list[dict] = []
    answers: dict[str, tuple[float, float]] = {}

    async def fake_decide(state, questions, **_):
        asked.append(questions)
        out = {}
        for key in questions:
            kind, k = key.split("_")
            title = state[f"EVENT_{k}"].split("Headline: ")[1].split("\n")[0]
            same, story = answers.get(title, (0.0, 0.0))
            out[key] = NoulAnswer(noul=same if kind == "same" else story)
        return Decisions(answers=out, model="typesafe/jev-test")

    monkeypatch.setattr(verify, "decide", fake_decide)
    monkeypatch.setattr(get_settings(), "prism_event_verify", "confirm")
    return asked, answers


def _proposal(event_id, tier="entity_overlap"):
    return clustering.Match(event_id=event_id, match_type=tier, match_score=0.9)


async def test_a_proposal_jev_confirms_attaches_under_its_own_tier(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    asked, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        proposed = await _event_with_member(s, f"Father demands arrests {tag}", _at(g, FLOOR * 3))
        answers[f"Father demands arrests {tag}"] = (0.93, 0.1)
        aid = await _incoming_article(s)
        match = await clustering._verified(s, [_proposal(proposed)], g, BLOCK, None, aid)
        assert match == clustering.Match(event_id=proposed, match_type="entity_overlap", match_score=0.93)
        assert set(asked[0]) >= {"same_1", "story_1"}, "one call asks both questions"
        await s.rollback()


async def test_a_proposal_jev_refuses_founds_a_record_and_keeps_the_follow_up_answer(jev):
    """IIT-Bombay, 2026-09: the parents' hunger strike was attached to the
    father's demand for arrests by shared actors. It is a later development."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        proposed = await _event_with_member(s, f"Father demands arrests {tag}", _at(g, FLOOR * 3))
        answers[f"Father demands arrests {tag}"] = (0.12, 0.91)
        aid = await _incoming_article(s)
        assert await clustering._verified(s, [_proposal(proposed)], g, BLOCK, None, aid) is None
        row = (await s.execute(text("SELECT noul, story_noul, mode FROM event_match_verdicts WHERE article_id = :a"),
                               {"a": str(aid)})).one()
        assert (row.noul, row.story_noul, row.mode) == (0.12, 0.91, "confirm")
        await s.rollback()


async def test_a_gist_candidate_nobody_proposed_attaches_as_verified(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        near = await _event_with_member(s, f"Bank strike deferred {tag}", _at(g, FLOOR / 2))
        answers[f"Bank strike deferred {tag}"] = (0.9, 0.0)
        aid = await _incoming_article(s)
        match = await clustering._verified(s, [], g, BLOCK, None, aid)
        assert match is not None and (match.event_id, match.match_type) == (near, "verified")
        await s.rollback()


async def test_a_proposal_without_a_gist_is_still_judged(jev):
    """No gist (the extractor wrote no summary): the proposal is asked on its
    text, with no distance recorded."""
    if not await _db_reachable():
        pytest.skip("no database")
    asked, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        proposed = await _event_with_member(s, f"Duronto stone pelting {tag}", g)
        answers[f"Duronto stone pelting {tag}"] = (0.2, 0.0)
        aid = await _incoming_article(s)
        assert await clustering._verified(s, [_proposal(proposed, "title_time")], None, BLOCK, None, aid) is None
        assert len(asked) == 1
        dist = (await s.execute(text("SELECT gist_distance FROM event_match_verdicts WHERE article_id = :a"),
                                {"a": str(aid)})).scalar_one()
        assert dist is None
        await s.rollback()


async def test_when_jev_cannot_answer_only_a_title_proposal_attaches(monkeypatch, jev):
    """An outage must not turn every retelling into a duplicate record — but the
    embedding and entity tiers (76%, 44%) are not trusted on their own either:
    a new record is the cheaper mistake (review, 2026-09-29)."""
    if not await _db_reachable():
        pytest.skip("no database")

    async def down(*_a, **_k):
        raise ConnectionError("jev down")

    monkeypatch.setattr(verify, "decide", down)
    g = _direction()
    async with session_scope() as s:
        proposed = await _event_with_member(s, "anything", _at(g, FLOOR * 3))
        aid = await _incoming_article(s)
        title, entity = _proposal(proposed, "title_time"), _proposal(proposed, "entity_overlap")
        assert await clustering._verified(s, [entity, title], g, BLOCK, None, aid) == title
        assert await clustering._verified(s, [title], g, None, None, aid) == title, "no text to judge"
        assert await clustering._verified(s, [entity], g, BLOCK, None, aid) is None
        await s.rollback()


async def test_two_tiers_proposing_one_record_ask_about_it_once(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    asked, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        proposed = await _event_with_member(s, f"Gill fit for first ODI {tag}", _at(g, FLOOR * 3))
        answers[f"Gill fit for first ODI {tag}"] = (0.9, 0.0)
        aid = await _incoming_article(s)
        match = await clustering._verified(
            s, [_proposal(proposed, "title_time"), _proposal(proposed, "entity_overlap")], g, BLOCK, None, aid)
        assert match.match_type == "title_time", "the first tier to propose it names the attach"
        assert [k for k in asked[0] if k.startswith("same")] == ["same_1"]
        await s.rollback()


async def test_confirm_runs_every_fuzzy_tier_and_hands_the_proposals_to_the_verifier(monkeypatch, jev):
    a, b = uuid.uuid4(), uuid.uuid4()
    seen = {}

    async def title(*_a, **_k):
        return clustering.Match(a, "title_time", 0.7)

    async def entities(*_a, **_k):
        return clustering.Match(b, "entity_overlap", 0.9)

    async def verified(session, proposals, *rest):
        seen["proposals"] = proposals
        return None

    async def nothing(*_a, **_k):
        return None

    monkeypatch.setattr(clustering, "_match_by_title", title)
    monkeypatch.setattr(clustering, "_match_by_entities", entities)
    monkeypatch.setattr(clustering, "_match_by_embedding", nothing)
    monkeypatch.setattr(clustering, "_boilerplate_body", nothing)
    monkeypatch.setattr(clustering, "_verified", verified)
    out = await clustering.find_event(None, cve_ids=[], url=None, title="An English title", published_at=None,
                                      embedding=[0.0] * 3, entity_slugs=["x"], verify_block=BLOCK, article_id=uuid.uuid4())
    assert out is None
    assert [p.event_id for p in seen["proposals"]] == [a, b]

    monkeypatch.setattr(get_settings(), "prism_event_verify", "live")
    out = await clustering.find_event(None, cve_ids=[], url=None, title="An English title", published_at=None,
                                      embedding=[0.0] * 3, entity_slugs=["x"], verify_block=BLOCK, article_id=uuid.uuid4())
    assert out == clustering.Match(a, "title_time", 0.7), "live: the first fuzzy tier still attaches on its own"


async def test_the_merge_judge_still_asks_only_the_same_happening(jev):
    asked, answers = jev
    c = verify.Candidate(event_id=uuid.uuid4(), distance=0.05)
    scored, _, _ = await verify.judge(article_id=uuid.uuid4(), block=BLOCK, candidates=[c],
                                      blocks={c.event_id: "First reported x.\nHeadline: t\nSummary: s"})
    assert list(asked[0]) == ["same_1"] and len(scored[0]) == 2


async def _follow_up_fixture(s, story: float):
    """An existing record, a new one founded by `aid`, and the verdict between them."""
    g = _direction()
    earlier = await _event_with_member(s, f"Earlier {uuid.uuid4().hex[:6]}", g)
    later = await _event_with_member(s, f"Later {uuid.uuid4().hex[:6]}", g)
    aid = await _incoming_article(s)
    await s.execute(text("INSERT INTO event_match_verdicts (article_id, event_id, noul, story_noul, model, mode) "
                         "VALUES (:a, :e, 0.1, :s, 'm', 'confirm')"), {"a": str(aid), "e": str(earlier), "s": story})
    return earlier, later, aid


async def test_a_new_record_is_linked_as_a_later_development_on_jevs_word():
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        earlier, later, aid = await _follow_up_fixture(s, 0.91)
        await consumer._link_follow_up(s, aid, later)
        link = (await s.execute(text("SELECT relation, confidence, method FROM event_links "
                                     "WHERE from_event_id = :f AND to_event_id = :t"),
                                {"f": str(earlier), "t": str(later)})).one()
        assert (link.relation, link.method) == ("leads_to", "verified") and link.confidence == 0.91
        await s.rollback()


async def test_under_the_floor_there_is_no_link():
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        earlier, later, aid = await _follow_up_fixture(s, get_settings().prism_follow_up_min - 0.01)
        await consumer._link_follow_up(s, aid, later)
        n = (await s.execute(text("SELECT count(*) FROM event_links WHERE to_event_id = :t"), {"t": str(later)})).scalar_one()
        assert n == 0
        await s.rollback()


async def test_a_verdict_without_a_follow_up_answer_never_names_the_new_column():
    """Review 2026-09-29: only the API container migrates. A worker on this code
    that started first wrote story_noul on every live verdict, the INSERT failed,
    and the verified tier stalled until the migration ran."""
    sql = []

    class _Session:
        async def execute(self, stmt, params=None):
            sql.append(str(stmt))

    c = verify.Candidate(event_id=uuid.uuid4(), distance=0.05)
    await verify.record(_Session(), article_id=uuid.uuid4(), scored=[(c, 0.9)], model="m", mode="live")
    await verify.record(_Session(), article_id=uuid.uuid4(), scored=[verify.Verdict(c, 0.1, 0.9)], model="m", mode="confirm")
    assert "story_noul" not in sql[0] and "story_noul" in sql[1]
