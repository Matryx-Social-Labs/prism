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
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import correlation.stories as stories
from api.main import app
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
        row = (await s.execute(text("SELECT id, status, member_event_ids FROM stories WHERE anchor_event_id = :a"),
                               {"a": str(anchor)})).one()
        assert set(row.member_event_ids) == {str(anchor), str(later)}
        assert row.status == "dormant", "a new story waits unlisted until the refresh finds it earned"
        await stories.refresh_stories(s)
        row = (await s.execute(text("SELECT status, source_count, velocity FROM stories WHERE id = :i"),
                               {"i": str(row.id)})).one()
        assert (row.status, row.source_count, row.velocity) == ("active", 2, 2.0)
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


async def _story_of_records(s, title_events: list[uuid.UUID], *, scope: str | None = None) -> uuid.UUID:
    """A persistent story over these records, anchored on the first, written directly."""
    sid = uuid.uuid4()
    await s.execute(text("INSERT INTO stories (id, slug, label, \"cast\", member_event_ids, hero_event_id, anchor_event_id, "
                         "scope, status, first_seen_at) VALUES (:i, :sl, 'x', '[]'::jsonb, CAST(:m AS jsonb), :a, :a, :sc, "
                         "'dormant', now())"),
                    {"i": str(sid), "sl": f"fx-{sid.hex[:12]}", "a": str(title_events[0]), "sc": scope,
                     "m": "[" + ",".join(f'"{e}"' for e in title_events) + "]"})
    for e in title_events:
        await s.execute(text("INSERT INTO story_events (event_id, story_id, facet) VALUES (:e, :s, 'event')"),
                        {"e": str(e), "s": str(sid)})
    return sid


async def test_the_established_story_wins_over_a_splinter_that_scored_higher(jev):
    """2026-10-02: two of the three Flydubai records outside the main story had
    the main story passing (0.87, 0.83) and a splinter scoring a hair higher
    (0.89, 0.85); the highest score took them, and the story stayed split."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        main = [await _event_with_member(s, f"Flydubai flight lands in Saudi Arabia {tag}", _at(g, 0.05)),
                await _event_with_member(s, f"Pilot hailed for landing {tag}", _at(g, 0.05))]
        splinter = [await _event_with_member(s, f"Captain explains the incident {tag}", _at(g, 0.06))]
        big, small = await _story_of_records(s, main), await _story_of_records(s, splinter)
        answers[f"Flydubai flight lands in Saudi Arabia {tag}"] = 0.87
        answers[f"Captain explains the incident {tag}"] = 0.89
        x = await _event_with_member(s, f"Video of bloodied captain emerges {tag}", g)
        await stories.assign_story(s, x)
        row = await _story_of(s, x)
        assert row.story_id == big and row.noul == 0.87
        both = (await s.execute(text("SELECT count(*) FROM story_verdicts WHERE event_id = :e AND noul >= 0.7"),
                                {"e": str(x)})).scalar_one()
        assert both == 2, "the splinter's passing verdict stays for the merge pass"
        assert small != big
        await s.rollback()


async def _published(s, eid: uuid.UUID, hours_ago: int) -> None:
    """Every report of the record published `hours_ago`; the record first reported then."""
    await s.execute(text("UPDATE events SET first_seen_at = now() - make_interval(hours => :h), "
                         "first_published_at = now() - make_interval(hours => :h) WHERE id = :e"),
                    {"h": hours_ago, "e": str(eid)})
    await s.execute(text("UPDATE raw_items SET published_at = now() - make_interval(hours => :h) WHERE id IN ("
                         "SELECT a.raw_item_id FROM event_memberships m JOIN articles a ON a.id = m.article_id "
                         "WHERE m.event_id = :e)"), {"h": hours_ago, "e": str(eid)})


async def test_refresh_counts_heat_by_publication_not_by_when_prism_read_it(jev):
    """A backlog read today of reports from two days ago is not trending: the
    velocity and the listing read each outlet's own publication time."""
    if not await _db_reachable():
        pytest.skip("no database")
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        old = [await _event_with_member(s, f"Old report {k} {tag}", _at(g, 0.05)) for k in range(2)]
        for e in old:
            await _published(s, e, 48)
        sid = await _story_of_records(s, old)
        await stories.refresh_stories(s, everything=True)
        row = (await s.execute(text("SELECT status, source_count, velocity FROM stories WHERE id = :i"),
                               {"i": str(sid)})).one()
        assert (row.status, row.source_count, row.velocity) == ("dormant", 2, 0.0)
        await s.rollback()


async def test_a_running_story_stays_listed_for_three_days_and_a_lone_record_is_never_listed(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        war = await _event_with_member(s, f"Strikes on Isfahan {tag}", g)
        await _published(s, war, 48)
        running = await _story_of_records(s, [war], scope=f"The 2026 Iran war {tag}")
        lone = await _story_of_records(s, [await _event_with_member(s, f"Lone report {tag}", _direction())])
        await stories.refresh_stories(s, everything=True)
        status = dict((await s.execute(text("SELECT id, status FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                                       {"i": [str(running), str(lone)]})).all())
        assert status == {running: "active", lone: "dormant"}
        await _published(s, war, 80)
        await stories.refresh_stories(s, everything=True)
        assert (await s.execute(text("SELECT status FROM stories WHERE id = :i"),
                                {"i": str(running)})).scalar_one() == "dormant"
        await s.rollback()


async def test_a_judge_built_story_is_served_verified_running_first_and_owns_its_records():
    """Live: the API reads the judge-built story as verified (a Leiden grouping
    stays provisional), a running story leads the list, and a record's page
    finds its story through story_events."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    ev, run, leiden = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    try:
        async with session_scope() as s:
            await s.execute(text("INSERT INTO events (id, title, sector) VALUES (:i, 'Strikes on Isfahan', 'other')"),
                            {"i": str(ev)})
            await s.execute(text("INSERT INTO stories (id, slug, label, \"cast\", member_event_ids, hero_event_id, "
                                 "anchor_event_id, scope, source_count, velocity, status) VALUES (:i, :sl, 'Iran war', "
                                 "'[]'::jsonb, CAST(:m AS jsonb), :e, :e, 'The 2026 Iran war', 2, 0, 'active')"),
                            {"i": str(run), "sl": f"run-{tag}", "e": str(ev), "m": f'["{ev}", "{uuid.uuid4()}"]'})
            await s.execute(text("INSERT INTO story_events (event_id, story_id, facet) VALUES (:e, :s, 'event')"),
                            {"e": str(ev), "s": str(run)})
            # A Leiden story holding the same record, refreshed later: the old lookup's pick.
            await s.execute(text("INSERT INTO stories (id, slug, label, \"cast\", member_event_ids, source_count, "
                                 "velocity, status, last_updated_at) VALUES (:i, :sl, 'Leiden', '[]'::jsonb, "
                                 "CAST(:m AS jsonb), 9, 99, 'active', now() + interval '1 minute')"),
                            {"i": str(leiden), "sl": f"leiden-{tag}", "m": f'["{ev}"]'})
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            listed = (await ac.get("/api/v1/trending?limit=50")).json()["stories"]
            order = [x["slug"] for x in listed]
            assert order.index(f"run-{tag}") < order.index(f"leiden-{tag}"), "a running story leads"
            status = {x["slug"]: x["boundary_status"] for x in listed}
            assert (status[f"run-{tag}"], status[f"leiden-{tag}"]) == ("verified", "provisional")
            detail = (await ac.get(f"/api/v1/trending/run-{tag}")).json()
            assert detail["boundary_status"] == "verified" and detail["branches"] is None
            assert (await ac.get(f"/api/v1/events/{ev}")).json()["story_slug"] == f"run-{tag}"
            # A story of one is the record itself: no story section, and no Leiden grouping instead.
            await _drop_to_one(ev, run)
            assert (await ac.get(f"/api/v1/events/{ev}")).json()["story_slug"] is None
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM story_events WHERE event_id = :e"), {"e": str(ev)})
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"), {"i": [str(run), str(leiden)]})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(ev)})


async def _drop_to_one(ev: uuid.UUID, sid: uuid.UUID) -> None:
    async with session_scope() as s:
        await s.execute(text("UPDATE stories SET member_event_ids = CAST(:m AS jsonb) WHERE id = :i"),
                        {"m": f'["{ev}"]', "i": str(sid)})


async def test_a_story_an_outlet_joins_after_two_hours_is_still_reread(jev):
    """An outlet attaching to an existing record does not touch the story row: a
    two-record story from one outlet, joined three hours ago, must still be read
    when a second outlet arrives, or it is never listed."""
    if not await _db_reachable():
        pytest.skip("no database")
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        recs = [await _event_with_member(s, f"Two records {k} {tag}", _at(g, 0.05)) for k in range(2)]
        sid = await _story_of_records(s, recs)
        await s.execute(text("UPDATE stories SET last_updated_at = now() - interval '3 hours' WHERE id = :i"),
                        {"i": str(sid)})
        await stories.refresh_stories(s)
        assert (await s.execute(text("SELECT status FROM stories WHERE id = :i"), {"i": str(sid)})).scalar_one() == "active"
        await s.rollback()
