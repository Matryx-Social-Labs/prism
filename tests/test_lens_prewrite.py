"""Lens briefs are written before anyone taps, and the one written on a tap is fast.

Audit 2026-09-27: 92% of Markets taps in 48 h found no brief (the analysis pass
wrote only the sector's primary lens, and single-source stories never reach
it), so the reader waited on generate_briefs — glm-5.3-flash at default
reasoning, 2,758 of 3,000 tokens spent thinking, 25 s.
"""

import datetime as dt
import json
import uuid

import pytest
from sqlalchemy import text

import correlation.briefs as briefs
import correlation.consumer as consumer
from common import budget
from common.db import session_scope
from common.llm import REASONING_OFF
from common.stream import get_redis
from correlation.schemas import EventAnalysis, LensBriefs, LensRead
from tests.test_projection_summary import _add_member, _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _event(s, *, sector, projection, hours_ago=1) -> uuid.UUID:
    eid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO events (id, title, summary, sector, projection, last_updated_at) "
             "VALUES (:i, 'Prewrite record', 's', :sec, CAST(:p AS jsonb), :w)"),
        {"i": str(eid), "sec": sector, "p": json.dumps(projection),
         "w": dt.datetime.now(dt.UTC) - dt.timedelta(hours=hours_ago)},
    )
    return eid


async def _drop(ids):
    async with session_scope() as s:
        await s.execute(text("DELETE FROM events WHERE id::text = ANY(:e)"), {"e": [str(i) for i in ids]})


async def test_the_brief_is_written_without_thinking_aloud(monkeypatch):
    """The bake-off behind it is in correlation/briefs.BRIEF_MAX_TOKENS."""
    if not await _db_reachable():
        pytest.skip("no database")
    seen = {}

    async def chat(**kw):
        seen.update(kw)
        return LensBriefs(markets=LensRead(text="Written."))

    monkeypatch.setattr(briefs, "structured_chat", chat)
    async with session_scope() as s:
        eid = await _event(s, sector="business", projection={"finance": {"tickers": ["TCS"]}})
    try:
        out = await briefs.generate_briefs(eid, ["markets"])
    finally:
        await _drop([eid])
    assert out == {"markets": {"text": "Written.", "points": []}}
    assert seen["reasoning"] == REASONING_OFF
    assert seen["max_tokens"] <= 2000, "a ceiling a model can think its way through"
    assert seen["providers"] == ["together"]


async def test_the_analysis_writes_every_lens_the_story_offers(monkeypatch):
    """A politics story whose reports carry market facts offers Markets; the
    analysis used to write only politics' primary lens, the Reader."""
    if not await _db_reachable():
        pytest.skip("no database")
    asked = {}

    async def analysis(**kw):
        asked["prompt"] = json.dumps(kw["messages"])
        return EventAnalysis(briefs=LensBriefs(
            reader=LensRead(text="The reader read."), markets=LensRead(text="The markets read.", points=["watch"]),
        ))

    monkeypatch.setattr(consumer, "structured_chat", analysis)
    src, created = uuid.uuid4(), []
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO sources (id, slug, name, source_type, country, publisher) "
                 "VALUES (:i, :s, 'Prewrite Test', 'rss', 'IN', 'prewrite-test')"),
            {"i": str(src), "s": f"prewrite-{src.hex[:8]}"},
        )
        eid = await _event(s, sector="politics", projection={"finance": {"tickers": ["RELIANCE"]}})
        for n in range(2):
            created.append(await _add_member(s, eid, title="Tariff vote", summary="It passed.", source_id=src, minutes_ago=n))
    try:
        await consumer._analyze_event(eid)
        async with session_scope() as s:
            proj = (await s.execute(text("SELECT projection FROM events WHERE id = :i"), {"i": str(eid)})).scalar_one()
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
            for raw_id, art_id in created:
                await s.execute(text("DELETE FROM enrichments WHERE article_id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(raw_id)})
            await s.execute(text("DELETE FROM perspectives WHERE event_id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(src)})
    requested = asked["prompt"].split("Requested lenses: ", 1)[1].split("\\n", 1)[0]
    assert set(requested.split(", ")) == {"reader", "markets"}
    assert proj["lens_briefs"]["markets"] == "The markets read."


async def test_the_sweep_writes_what_recent_stories_offer_and_lack(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    calls = []
    async with session_scope() as s:
        single = await _event(s, sector="business", projection={})
        cyber = await _event(s, sector="politics", projection={"role_interests": ["cyber"]})
        written = await _event(s, sector="business", projection={"lens_briefs": {"markets": "Already."}})
        reader_only = await _event(s, sector="sports", projection={})
        stale = await _event(s, sector="business", projection={}, hours_ago=24 * 5)
    mine = {single, cyber, written, reader_only, stale}

    async def write(event_id, lenses):
        calls.append((event_id, sorted(lenses)))
        if event_id == cyber:
            return {}  # the model wrote nothing for this one
        return {slug: {"text": f"The {slug} read."} for slug in lenses}

    monkeypatch.setattr(briefs, "generate_briefs", write)
    monkeypatch.setattr(budget, "current", _balance(100.0))
    try:
        await briefs.sweep_lens_briefs(limit=10_000)
        first = sorted((str(e), lenses) for e, lenses in calls if e in mine)
        calls.clear()
        await briefs.sweep_lens_briefs(limit=10_000)
        second = [e for e, _ in calls if e in mine]
        async with session_scope() as s:
            proj = (await s.execute(text("SELECT projection FROM events WHERE id = :i"), {"i": str(single)})).scalar_one()
    finally:
        await _drop(mine)
        async for key in get_redis().scan_iter("prism:lens-sweep:*"):
            await get_redis().delete(key)
    assert first == sorted([(str(single), ["markets"]), (str(cyber), ["cyber"])])
    assert proj["lens_briefs"]["markets"] == "The markets read."
    assert second == [], "a story the model wrote nothing for held a place in the next batch"


async def test_the_sweep_spends_nothing_under_the_budget_floor(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    calls = []

    async def write(event_id, lenses):
        calls.append(event_id)
        return {}

    monkeypatch.setattr(briefs, "generate_briefs", write)
    monkeypatch.setattr(budget, "current", _balance(0.01))
    async with session_scope() as s:
        eid = await _event(s, sector="business", projection={})
    try:
        await briefs.sweep_lens_briefs(limit=10_000)
    finally:
        await _drop([eid])
        async for key in get_redis().scan_iter("prism:lens-sweep:*"):
            await get_redis().delete(key)
    assert calls == [], "the sweep paid the model under the budget floor"


def _balance(usd: float):
    async def current():
        return {"balance": usd, "at": 0}

    return current
