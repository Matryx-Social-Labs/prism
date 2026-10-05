"""Calibrated story floors, big-story centroids and the merge pass (2026-10-02).

- A running story's scope reads lower to Jev: 101 of 105 running-story
  judgements at 0.45-0.90 belonged, so its floor is prism_story_running_min.
- A big story is proposed by its centroid as well as by its nearest member.
- A split story is absorbed into the story it is part of, judged on its
  founding and latest reports at the join floor + MERGE_MARGIN, never the
  other way round for a running story.
Jev is mocked (tests/test_stories.jev): answers by the story's founding title or scope.
"""

import uuid

import pytest
from sqlalchemy import text

import correlation.stories as stories
from common.db import session_scope
from correlation import story_merge
from tests.test_stories import _story_of, _story_of_records, jev  # noqa: F401 — jev is a fixture
from tests.test_verified_tier import _at, _db_reachable, _direction, _event_with_member

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_a_running_story_takes_a_record_the_judge_reads_at_its_own_floor(jev):  # noqa: F811
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        a = await _event_with_member(s, f"Hockey semifinal {tag}", _at(g, 0.05))
        games = await _story_of_records(s, [a], scope=f"The 2026 Asian Games {tag}")
        b = [await _event_with_member(s, f"Hockey India awards {k} {tag}", _at(g, 0.05)) for k in range(2)]
        plain = await _story_of_records(s, b)  # bigger, and passing too: the running story still wins
        answers[f"The 2026 Asian Games {tag}"] = 0.65  # under the plain floor, over the running one
        answers[f"Hockey India awards 0 {tag}"] = 0.75
        x = await _event_with_member(s, f"Women's hockey team celebrates gold {tag}", g)
        await stories.assign_story(s, x)
        assert (await _story_of(s, x)).story_id == games
        assert plain != games
        await s.rollback()


async def test_a_big_story_is_proposed_by_its_centroid_when_no_member_is_near(monkeypatch, jev):  # noqa: F811
    """Each member 0.15 away (past NEIGHBOUR_DIST), their mean much nearer."""
    if not await _db_reachable():
        pytest.skip("no database")
    calls, answers = jev
    monkeypatch.setattr(stories, "BIG_STORY", 3)
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        members = [await _event_with_member(s, f"Iran war {k} {tag}", _at(g, 0.15)) for k in range(4)]
        war = await _story_of_records(s, members)
        answers[f"Iran war 0 {tag}"] = 0.9
        x = await _event_with_member(s, f"Rubio asks Iranian delegation to leave {tag}", g)
        await stories.assign_story(s, x)
        assert (await _story_of(s, x)).story_id == war
        await s.rollback()


async def _verdict(s, event_id, story_id, noul):
    await s.execute(text("INSERT INTO story_verdicts (event_id, story_id, noul, model) VALUES (:e, :s, :n, 'test')"),
                    {"e": str(event_id), "s": str(story_id), "n": noul})


async def test_a_splinter_is_planned_into_the_story_and_applied_once(jev):  # noqa: F811
    """A record sits in the main story and the judge also passed it for a
    splinter: the splinter, read on its own reports, is part of the main story."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        main = [await _event_with_member(s, f"Flydubai flight lands {k} {tag}", _at(g, 0.05)) for k in range(3)]
        big = await _story_of_records(s, main)
        splinter_recs = [await _event_with_member(s, f"Captain explains {k} {tag}", _at(g, 0.05)) for k in range(2)]
        small = await _story_of_records(s, splinter_recs)
        await _verdict(s, main[2], small, 0.80)
        answers[f"Flydubai flight lands 0 {tag}"] = 0.86  # >= 0.70 + 0.15
        merges = [m for m in await story_merge.plan_merges(s, hours=2) if m["story"] == small]
        assert [(m["into"], m["records"]) for m in merges] == [(big, 2)]
        assert await story_merge.apply_merges(s, merges) == 1
        assert {(await _story_of(s, e)).story_id for e in splinter_recs} == {big}
        assert (await s.execute(text("SELECT merged_into FROM stories WHERE id = :i"), {"i": str(small)})).scalar_one() == big
        assert await story_merge.apply_merges(s, merges) == 0, "a merged story is never absorbed twice"
        await s.rollback()


async def test_a_reading_under_the_margin_keeps_the_stories_apart(jev):  # noqa: F811
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        main = [await _event_with_member(s, f"Rupee slumps {k} {tag}", _at(g, 0.05)) for k in range(3)]
        await _story_of_records(s, main)
        small = await _story_of_records(s, [await _event_with_member(s, f"Gold prices drop {tag}", _at(g, 0.05))])
        await _verdict(s, main[1], small, 0.75)
        answers[f"Rupee slumps 0 {tag}"] = 0.84  # passes the join floor, not the merge margin
        assert [m for m in await story_merge.plan_merges(s, hours=2) if m["story"] == small] == []
        await s.rollback()


async def test_a_running_story_is_never_absorbed_and_takes_merges_at_its_own_margin(jev):  # noqa: F811
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        a = await _event_with_member(s, f"Strikes on Isfahan {tag}", _at(g, 0.05))
        war = await _story_of_records(s, [a], scope=f"The 2026 Iran war {tag}")
        recs = [await _event_with_member(s, f"Oil tops 100 dollars {k} {tag}", _at(g, 0.05)) for k in range(3)]
        oil = await _story_of_records(s, recs)  # bigger than the running story, and still absorbed into it
        await _verdict(s, recs[0], war, 0.70)
        answers[f"The 2026 Iran war {tag}"] = 0.76  # >= 0.60 + 0.15
        merges = [m for m in await story_merge.plan_merges(s, hours=2) if war in (m["story"], m["into"])]
        assert [(m["story"], m["into"]) for m in merges] == [(oil, war)]
        await s.rollback()


async def test_a_pass_never_chains_a_story_through_another_merge(jev):  # noqa: F811
    """A splinter of a splinter: (A, B) and (B, C) both pass. One pass plans one
    of them; carrying A into C would join it to a story it was never read against."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        c_recs = [await _event_with_member(s, f"C main {k} {tag}", _at(g, 0.05)) for k in range(3)]
        b_recs = [await _event_with_member(s, f"B middle {k} {tag}", _at(g, 0.05)) for k in range(2)]
        a_recs = [await _event_with_member(s, f"A small {tag}", _at(g, 0.05))]
        c, b, a = (await _story_of_records(s, c_recs), await _story_of_records(s, b_recs),
                   await _story_of_records(s, a_recs))
        await _verdict(s, c_recs[0], b, 0.80)
        await _verdict(s, b_recs[0], a, 0.80)
        answers[f"C main 0 {tag}"] = 0.9
        answers[f"B middle 0 {tag}"] = 0.9
        mine = [m for m in await story_merge.plan_merges(s, hours=2) if {m["story"], m["into"]} & {a, b, c}]
        assert len(mine) == 1
        await s.rollback()


async def test_the_backlog_pairs_a_far_small_story_with_the_big_story_whose_centre_is_near(monkeypatch, jev):  # noqa: F811
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    monkeypatch.setattr(story_merge, "BIG_STORY", 3)
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        war = await _story_of_records(s, [await _event_with_member(s, f"War {k} {tag}", _at(g, 0.15)) for k in range(4)])
        small = await _story_of_records(s, [await _event_with_member(s, f"Delegation expelled {tag}", g)])
        answers[f"War 0 {tag}"] = 0.9
        assert [m for m in await story_merge.plan_merges(s, hours=2) if m["story"] == small] == []
        merges = [m for m in await story_merge.plan_merges(s, hours=2, centroid=True) if m["story"] == small]
        assert [m["into"] for m in merges] == [war]
        await s.rollback()


async def test_a_big_story_takes_every_splinter_in_one_pass(jev):  # noqa: F811
    """2026-10-02: a pass that let a story into one merge only folded 19 of the
    backlog's splinters: the Iran war could absorb one splinter an hour."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    g, tag = _direction(), uuid.uuid4().hex[:6]
    async with session_scope() as s:
        main = [await _event_with_member(s, f"Big story {k} {tag}", _at(g, 0.05)) for k in range(4)]
        big = await _story_of_records(s, main)
        splinters = [await _story_of_records(s, [await _event_with_member(s, f"Splinter {k} {tag}", _at(g, 0.05))])
                     for k in range(3)]
        for k, sp in enumerate(splinters):
            await _verdict(s, main[k], sp, 0.80)
        answers[f"Big story 0 {tag}"] = 0.9
        merges = [m for m in await story_merge.plan_merges(s, hours=2) if m["into"] == big]
        assert sorted(m["story"] for m in merges) == sorted(splinters)
        await s.rollback()


def test_a_pass_admits_star_merges_and_never_a_chain():
    a, b, c, d = (uuid.uuid4() for _ in range(4))
    # B was absorbed into C: nothing more for B, either way round.
    assert not story_merge.admissible(b, d, absorbed={b}, targets={c})
    assert not story_merge.admissible(a, b, absorbed={b}, targets={c})
    # A was absorbed into B: B takes merges now, so B is never absorbed into C.
    assert not story_merge.admissible(b, c, absorbed={a}, targets={b})
    # C takes merges: it takes another.
    assert story_merge.admissible(d, c, absorbed={b}, targets={c})
