"""The 0.65-0.85 band: a second judgement on the opening texts.

Measured 2026-10-01 on 160 blind-labelled refused candidates since the confirm
flip: at 0.75-0.85, 51 of 60 were the same happening and the 0.85 floor turned
every one into a duplicate record (~14% of new records). One more Jev call with
both reports' opening text, attaching at >= 0.80 when it does not also call the
article a later development, took 52 of them at precision 0.98 (one wrong: two
countries' probes of one incident). Chat models (flash-lite, glm, haiku, 3.5
flash) read "same" too liberally, 0.76-0.89, at 2-100x the cost.

Jev is mocked; under test is who gets the second question, what its answer
does in each mode, and that a failure leaves the article to found its own record.
"""

import uuid

import pytest
from sqlalchemy import text

import correlation.clustering as clustering
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
    """First call: (same, later development) per event title. The second call
    (REPORT/RECORD with opening texts): its own answers per title."""
    calls: list[dict] = []
    first: dict[str, tuple[float, float]] = {}
    ledes: dict[str, tuple[float, float]] = {}

    async def fake_decide(state, questions, **_):
        calls.append(state)
        out = {}
        if "RECORD" in state:
            title = state["RECORD"].split("Headline: ")[1].split("\n")[0]
            same, story = ledes.get(title, (0.0, 0.0))
            return Decisions(answers={"same": NoulAnswer(noul=same), "story": NoulAnswer(noul=story)},
                             model="typesafe/jev-test")
        for key in questions:
            kind, k = key.split("_")
            title = state[f"EVENT_{k}"].split("Headline: ")[1].split("\n")[0]
            same, story = first.get(title, (0.0, 0.0))
            out[key] = NoulAnswer(noul=same if kind == "same" else story)
        return Decisions(answers=out, model="typesafe/jev-test")

    monkeypatch.setattr(verify, "decide", fake_decide)
    monkeypatch.setattr(get_settings(), "prism_event_verify", "confirm")
    monkeypatch.setattr(get_settings(), "prism_event_escalate", "live")
    return calls, first, ledes


async def _band_case(s, first, ledes, *, same=0.78, story=0.2, lede=(0.9, 0.1)):
    g, tag = _direction(), uuid.uuid4().hex[:6]
    title = f"Rubio asks Iranian delegation to leave {tag}"
    eid = await _event_with_member(s, title, _at(g, FLOOR / 2))
    first[title], ledes[title] = (same, story), lede
    return eid, g, await _incoming_article(s)


async def test_a_paraphrase_in_the_band_attaches_when_the_opening_texts_agree(jev):
    """2026-10-01: "Marco Rubio reportedly ordered Iranian delegation to leave"
    scored 0.83 and 0.81 against two records of the same happening and founded a third."""
    if not await _db_reachable():
        pytest.skip("no database")
    calls, first, ledes = jev
    async with session_scope() as s:
        eid, g, aid = await _band_case(s, first, ledes)
        match = await clustering._verified(s, [], g, BLOCK, None, aid)
        assert match == clustering.Match(event_id=eid, match_type="escalated", match_score=0.9)
        assert len(calls) == 2 and "Opening text: body" in calls[1]["RECORD"]
        row = (await s.execute(text("SELECT noul, lede_noul, lede_story_noul FROM event_match_verdicts "
                                    "WHERE article_id = :a"), {"a": str(aid)})).one()
        assert (row.noul, row.lede_noul, row.lede_story_noul) == (0.78, 0.9, 0.1)
        await s.rollback()


async def test_a_later_development_is_refused_on_the_second_reading(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    _, first, ledes = jev
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes, lede=(0.9, 0.88))
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        await s.rollback()


async def test_a_weak_second_reading_founds_a_record(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    _, first, ledes = jev
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes, lede=(0.79, 0.1))
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        await s.rollback()


async def test_under_the_floor_nobody_is_asked_twice(jev):
    """Below 0.65 the band read ~53% the same happening; not worth a second call."""
    if not await _db_reachable():
        pytest.skip("no database")
    calls, first, ledes = jev
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes, same=0.6)
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        assert len(calls) == 1
        await s.rollback()


async def test_shadow_asks_and_records_but_never_attaches(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, first, ledes = jev
    monkeypatch.setattr(get_settings(), "prism_event_escalate", "shadow")
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes)
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        assert len(calls) == 2
        lede = (await s.execute(text("SELECT lede_noul FROM event_match_verdicts WHERE article_id = :a"),
                                {"a": str(aid)})).scalar_one()
        assert lede == 0.9
        await s.rollback()


async def test_off_asks_once(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, first, ledes = jev
    monkeypatch.setattr(get_settings(), "prism_event_escalate", "off")
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes)
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        assert len(calls) == 1
        await s.rollback()


async def test_a_failed_second_call_founds_a_record_and_leaves_the_session_usable(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, first, ledes = jev
    real = verify.decide

    async def second_fails(state, questions, **kw):
        if "RECORD" in state:
            raise ConnectionError("decisions unavailable")
        return await real(state, questions, **kw)

    monkeypatch.setattr(verify, "decide", second_fails)
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes)
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        assert (await s.execute(text("SELECT 1"))).scalar_one() == 1
        await s.rollback()
