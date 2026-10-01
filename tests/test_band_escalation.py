"""The 0.65-0.85 band: a second judgement on the opening texts, in both orders.

Measured 2026-10-01 on 160 blind-labelled refused candidates since the confirm
flip: at 0.75-0.85, 51 of 60 were the same happening and the 0.85 floor turned
every one into a duplicate record (~14% of new records). Asking Jev which of
same / later development / different the two reports are, with both opening
texts, once in each order and attaching only when both orders give "same"
>= 0.80, took 62% of the band's duplicates at precision 0.97 (the first
version, two yes/no questions in one order: 49% at 0.98). Asking in both orders
follows ComEM (COLING'25): a judge's answer depends on which text it reads first.
Chat models (flash-lite, glm, haiku, 3.5 flash) read "same" too liberally.

Jev is mocked; under test is who gets the second question, what its answers do
in each mode, and that a failure leaves the article to found its own record.
"""

import uuid

import pytest
from sqlalchemy import text

import correlation.clustering as clustering
import correlation.verify as verify
from common.config import get_settings
from common.db import session_scope
from common.decisions import ChoiceAnswer, Decisions, NoulAnswer
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
    """First call: (same, later development) per event title. The second
    reading (REPORT_A / REPORT_B with opening texts): p(same) per title for
    (article read first, record read first)."""
    calls: list[dict] = []
    first: dict[str, tuple[float, float]] = {}
    ledes: dict[str, tuple[float, float]] = {}

    async def fake_decide(state, questions, **_):
        calls.append(state)
        if "REPORT_A" in state:
            record_first = state["REPORT_A"].startswith("First reported")
            record = state["REPORT_A"] if record_first else state["REPORT_B"]
            title = record.split("Headline: ")[1].split("\n")[0]
            p = ledes.get(title, (0.0, 0.0))[1 if record_first else 0]
            return Decisions(answers={"relation": ChoiceAnswer(
                choice="same" if p >= 0.5 else "follow_up", confidence=max(p, 1 - p),
                probabilities={"same": p, "follow_up": 1 - p, "different": 0.0})}, model="typesafe/jev-test")
        out = {}
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


async def _band_case(s, first, ledes, *, same=0.78, story=0.2, lede=(0.9, 0.85)):
    g, tag = _direction(), uuid.uuid4().hex[:6]
    title = f"Rubio asks Iranian delegation to leave {tag}"
    eid = await _event_with_member(s, title, _at(g, FLOOR / 2))
    first[title], ledes[title] = (same, story), lede
    return eid, g, await _incoming_article(s)


async def test_a_paraphrase_in_the_band_attaches_when_both_orders_agree(jev):
    """2026-10-01: "Marco Rubio reportedly ordered Iranian delegation to leave"
    scored 0.83 and 0.81 against two records of the same happening and founded a third."""
    if not await _db_reachable():
        pytest.skip("no database")
    calls, first, ledes = jev
    async with session_scope() as s:
        eid, g, aid = await _band_case(s, first, ledes)
        match = await clustering._verified(s, [], g, BLOCK, None, aid)
        assert match == clustering.Match(event_id=eid, match_type="escalated", match_score=0.85)
        assert len(calls) == 3, "one first reading, then one in each order"
        assert {c["REPORT_A"][:9] for c in calls[1:]} == {"Published", "First rep"}
        assert all("Opening text: body" in c["REPORT_A"] for c in calls[1:])
        row = (await s.execute(text("SELECT noul, lede_noul, lede_story_noul FROM event_match_verdicts "
                                    "WHERE article_id = :a"), {"a": str(aid)})).one()
        assert (row.noul, row.lede_noul, round(row.lede_story_noul, 2)) == (0.78, 0.85, 0.15)
        await s.rollback()


async def test_the_orders_must_agree(jev):
    """A judge that says "same" only when it reads the article first is not sure."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, first, ledes = jev
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes, lede=(0.92, 0.6))
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        await s.rollback()


async def test_a_later_development_is_refused_on_the_second_reading(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    _, first, ledes = jev
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes, lede=(0.2, 0.3))
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        await s.rollback()


async def test_a_weak_second_reading_founds_a_record(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    _, first, ledes = jev
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes, lede=(0.79, 0.95))
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
        assert len(calls) == 3
        lede = (await s.execute(text("SELECT lede_noul FROM event_match_verdicts WHERE article_id = :a"),
                                {"a": str(aid)})).scalar_one()
        assert lede == 0.85
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
        if "REPORT_A" in state:
            raise ConnectionError("decisions unavailable")
        return await real(state, questions, **kw)

    monkeypatch.setattr(verify, "decide", second_fails)
    async with session_scope() as s:
        _, g, aid = await _band_case(s, first, ledes)
        assert await clustering._verified(s, [], g, BLOCK, None, aid) is None
        assert (await s.execute(text("SELECT 1"))).scalar_one() == 1
        await s.rollback()
