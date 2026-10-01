"""Stories that persist: a record joins one story at birth, on the judge's word.

Measured 2026-10-01 (.claude/plans/stories-breaking-segments.plan.md §2.3): the
global Leiden partition held 102 Flydubai records in 35 groups; proposing the
stories of a record's gist neighbours and asking Jev "part of this story?"
(star to the story, never record-to-record chaining) put 92% in one story, at
attach precision 0.92-0.97 on 60 read.

Jev is mocked; under test is who gets proposed, what an answer does, and that
a record always ends in exactly one story.
"""

import uuid

import pytest
from sqlalchemy import text

import correlation.stories as stories
from common.config import get_settings
from common.db import session_scope
from common.decisions import ChoiceAnswer, Decisions, NoulAnswer
from tests.test_verified_tier import _at, _db_reachable, _direction, _event_with_member

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture
def jev(monkeypatch):
    """part_of_story per story-anchor title; facet 'investigation' unless set. Records each state."""
    calls: list[dict] = []
    answers: dict[str, float] = {}

    async def fake_decide(state, questions, **_):
        calls.append(state)
        out = {}
        for key in questions:
            kind, k = key.split("_")
            block = state[f"STORY_{k}"]
            line = next(ln for ln in block.split("\n") if ln.startswith(("Founding report: ", "Running story: ")))
            title = line.split(": ", 1)[1].split(". ")[0]
            if kind == "part":
                out[key] = NoulAnswer(noul=answers.get(title, 0.0))
            else:
                out[key] = ChoiceAnswer(choice="investigation", confidence=0.9)
        return Decisions(answers=out, model="typesafe/jev-test")

    monkeypatch.setattr(stories, "decide", fake_decide)
    monkeypatch.setattr(get_settings(), "prism_stories", "shadow")
    return calls, answers


async def _story_of(s, event_id):
    return (await s.execute(text("SELECT se.story_id, se.noul, se.facet, st.status, st.anchor_event_id "
                                 "FROM story_events se JOIN stories st ON st.id = se.story_id "
                                 "WHERE se.event_id = :e"), {"e": str(event_id)})).one_or_none()


async def test_a_record_with_no_neighbours_founds_its_own_story(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, _ = jev
    async with session_scope() as s:
        eid = await _event_with_member(s, f"Flight diverted to Saudi Arabia {uuid.uuid4().hex[:6]}", _direction())
        await stories.assign_story(s, eid)
        row = await _story_of(s, eid)
        assert row is not None and row.anchor_event_id == eid and row.facet == "event"
        assert row.status == "shadow", "shadow stories are written, never served"
        assert calls == []
        await s.rollback()


async def test_a_record_near_a_story_joins_it_on_the_judges_word(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        anchor = await _event_with_member(s, f"Flight diverted {tag}", g)
        await stories.assign_story(s, anchor)
        later = await _event_with_member(s, f"UAE opens probe {tag}", _at(g, 0.05))
        answers[f"Flight diverted {tag}"] = 0.9
        await stories.assign_story(s, later)
        first, second = await _story_of(s, anchor), await _story_of(s, later)
        assert second.story_id == first.story_id and second.noul == 0.9 and second.facet == "investigation"
        members = (await s.execute(text("SELECT member_event_ids FROM stories WHERE id = :i"),
                                   {"i": str(first.story_id)})).scalar_one()
        assert members == [], "a shadow story is invisible to search and the record page"
        verdict = (await s.execute(text("SELECT noul FROM story_verdicts WHERE event_id = :e"),
                                   {"e": str(later)})).scalar_one()
        assert verdict == 0.9
        assert "Founding report: Flight diverted" in calls[0]["STORY_1"]
        await s.rollback()


async def test_a_neighbour_the_judge_refuses_founds_a_new_story(jev):
    """Same topic, different story: two CVEs, two diseases (2026-09-09 read)."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        a = await _event_with_member(s, f"Ubuntu snap-confine flaw {tag}", g)
        await stories.assign_story(s, a)
        b = await _event_with_member(s, f"OpenWrt DHCPv6 flaw {tag}", _at(g, 0.05))
        answers[f"Ubuntu snap-confine flaw {tag}"] = 0.4
        await stories.assign_story(s, b)
        assert (await _story_of(s, a)).story_id != (await _story_of(s, b)).story_id
        await s.rollback()


async def test_a_far_record_is_never_proposed(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        a = await _event_with_member(s, f"Monsoon withdraws {tag}", g)
        await stories.assign_story(s, a)
        b = await _event_with_member(s, f"Kohli 15000 runs {tag}", _at(g, stories.NEIGHBOUR_DIST * 2))
        answers[f"Monsoon withdraws {tag}"] = 0.99
        await stories.assign_story(s, b)
        assert calls == [] and (await _story_of(s, a)).story_id != (await _story_of(s, b)).story_id
        await s.rollback()


async def test_a_verified_follow_up_proposes_its_story_without_a_near_gist(jev):
    """The verifier's later-development link at ingest is the strongest story evidence."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        a = await _event_with_member(s, f"Student dies at IIT {tag}", g)
        await stories.assign_story(s, a)
        b = await _event_with_member(s, f"Parents begin hunger strike {tag}", _direction())
        await s.execute(text("INSERT INTO event_links (id, from_event_id, to_event_id, relation, confidence, method) "
                             "VALUES (:i, :f, :t, 'leads_to', 0.9, 'verified')"),
                        {"i": str(uuid.uuid4()), "f": str(a), "t": str(b)})
        answers[f"Student dies at IIT {tag}"] = 0.88
        await stories.assign_story(s, b)
        assert (await _story_of(s, b)).story_id == (await _story_of(s, a)).story_id
        await s.rollback()


async def test_a_running_story_is_judged_on_its_scope(jev):
    """Medal by medal, no record is a development of another; the 2026 Asian
    Games hold together only through a founder-written scope."""
    if not await _db_reachable():
        pytest.skip("no database")
    calls, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        a = await _event_with_member(s, f"Squash team wins bronze {tag}", g)
        await stories.assign_story(s, a)
        sid = (await _story_of(s, a)).story_id
        scope = f"The 2026 Asian Games {tag}"
        await s.execute(text("UPDATE stories SET scope = :sc WHERE id = :i"), {"sc": scope, "i": str(sid)})
        b = await _event_with_member(s, f"Hockey team reaches final {tag}", _at(g, 0.06))
        answers[scope] = 0.92
        await stories.assign_story(s, b)
        assert (await _story_of(s, b)).story_id == sid
        assert calls[0]["STORY_1"].startswith("Running story: The 2026 Asian Games")
        await s.rollback()


async def test_assignment_is_once_and_off_does_nothing(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        eid = await _event_with_member(s, f"Bank strike deferred {uuid.uuid4().hex[:6]}", _direction())
        monkeypatch.setattr(get_settings(), "prism_stories", "off")
        await stories.assign_story(s, eid)
        assert await _story_of(s, eid) is None
        monkeypatch.setattr(get_settings(), "prism_stories", "shadow")
        await stories.assign_story(s, eid)
        first = await _story_of(s, eid)
        await stories.assign_story(s, eid)
        n = (await s.execute(text("SELECT count(*) FROM story_events WHERE event_id = :e"),
                             {"e": str(eid)})).scalar_one()
        assert n == 1 and (await _story_of(s, eid)).story_id == first.story_id
        await s.rollback()


async def test_a_failed_judge_founds_a_story_and_the_session_stays_usable(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    g, tag = _direction(), uuid.uuid4().hex[:6]

    async def down(*_, **__):
        raise ConnectionError("decisions unavailable")

    async with session_scope() as s:
        a = await _event_with_member(s, f"Gujarat award for pilot {tag}", g)
        await stories.assign_story(s, a)
        monkeypatch.setattr(stories, "decide", down)
        b = await _event_with_member(s, f"Pilot to get Gujarat Garima {tag}", _at(g, 0.04))
        await stories.assign_story(s, b)
        assert (await _story_of(s, b)).anchor_event_id == b
        await s.rollback()


async def test_a_live_story_lists_its_members_for_the_serving_queries(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    monkeypatch.setattr(get_settings(), "prism_stories", "live")
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        anchor = await _event_with_member(s, f"Pune students drown {tag}", g)
        await stories.assign_story(s, anchor)
        later = await _event_with_member(s, f"Coaching institute owner held {tag}", _at(g, 0.05))
        answers[f"Pune students drown {tag}"] = 0.9
        await stories.assign_story(s, later)
        row = (await s.execute(text("SELECT status, member_event_ids FROM stories WHERE anchor_event_id = :a"),
                               {"a": str(anchor)})).one()
        assert row.status == "active" and set(row.member_event_ids) == {str(anchor), str(later)}
        await s.rollback()


async def test_a_story_absorbed_into_a_running_story_moves_every_record_and_redirects(jev):
    """The Iran war was 48 stories in the prototype; a founder-created running
    story absorbs the ones its scope covers, and their links redirect."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        a = await _event_with_member(s, f"Iran proposes Hormuz deal {tag}", g)
        await stories.assign_story(s, a)
        b = await _event_with_member(s, f"Trump rejects Hormuz deal {tag}", _at(g, 0.05))
        answers[f"Iran proposes Hormuz deal {tag}"] = 0.9
        await stories.assign_story(s, b)
        small = (await _story_of(s, a)).story_id
        running = await stories.create_running_story(s, title=f"Iran war {tag}", scope=f"The 2026 Iran war {tag}",
                                                     anchor_event_id=a)
        moved = await stories.absorb(s, running, small)
        assert moved == 2
        assert (await _story_of(s, a)).story_id == running and (await _story_of(s, b)).story_id == running
        row = (await s.execute(text("SELECT merged_into, status FROM stories WHERE id = :i"), {"i": str(small)})).one()
        assert (row.merged_into, row.status) == (running, "shadow"), "a shadow story stays unserved when absorbed"
        await s.rollback()
