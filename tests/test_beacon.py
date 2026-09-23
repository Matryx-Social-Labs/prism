"""The usage beacon (admin dashboard, phase 3; founder decisions D2/D3).

Pinned: a page view is counted once as a view and once as a visitor per day;
a second view from the same visitor is not a second visitor; bots, unknown
words and a visitor past the day's cap are not counted; nothing is counted
while Redis is away (an uncapped counter would let a script write the numbers
investors are shown); and a signed-in beacon records the day, and only the day.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth, stream, usage
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


@pytest.fixture(autouse=True)
def _fresh_redis(monkeypatch):
    """The Redis client is a module global bound to the event loop that first
    used it; another test module on another loop leaves one behind, and the
    beacon — which fails closed — would then count nothing."""
    monkeypatch.setattr(stream, "_redis", None)


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _count(event: str, dim: str = "") -> int:
    async with session_scope() as s:
        return (await s.execute(text("SELECT coalesce(sum(count), 0) FROM usage_daily WHERE day = :d AND event = :e AND dim = :m"),
                                {"d": usage.today(), "e": event, "m": dim})).scalar()


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


def _reader() -> dict[str, str]:
    """A browser nobody has seen today: the visitor hash is salt + IP + UA."""
    return {"user-agent": f"Mozilla/5.0 (iPhone) test-{uuid.uuid4().hex}"}


async def test_the_rules_hold_without_a_database():
    usage.demo()


async def test_a_view_counts_once_as_a_visitor_per_day():
    if not await _db_reachable():
        pytest.skip("no database")
    views, visitors = await _count("view", "story"), await _count("visitors")
    h = _reader()
    async with _client() as c:
        assert (await c.post("/api/v1/beacon", json={"e": "view", "d": "story"}, headers=h)).status_code == 204
        assert (await c.post("/api/v1/beacon", json={"e": "view", "d": "story"}, headers=h)).status_code == 204
    assert await _count("view", "story") == views + 2
    assert await _count("visitors") == visitors + 1


async def test_bots_unknown_words_and_questions_are_not_counted():
    if not await _db_reachable():
        pytest.skip("no database")
    before = await _count("view", "story")
    asks = await _count("ask", "bar")
    async with _client() as c:
        await c.post("/api/v1/beacon", json={"e": "view", "d": "story"},
                     headers={"user-agent": "Mozilla/5.0 (compatible; Googlebot/2.1)"})
        await c.post("/api/v1/beacon", json={"e": "view", "d": "story"}, headers={"user-agent": ""})
        r = await c.post("/api/v1/beacon", json={"e": "view", "d": "story/9f3c"}, headers=_reader())
        assert r.status_code == 204
        # The one place a reader's own words could leak is Ask; its word must be a slug.
        await c.post("/api/v1/beacon", json={"e": "ask", "d": "why did the rbi cut rates"}, headers=_reader())
        assert (await c.post("/api/v1/beacon", json={"e": "admin", "d": "x"}, headers=_reader())).status_code == 422
    assert await _count("view", "story") == before
    assert await _count("ask", "bar") == asks
    async with session_scope() as s:
        leaked = (await s.execute(text("SELECT count(*) FROM usage_daily WHERE dim LIKE '%rbi%' OR dim LIKE '%/%'"))).scalar()
    assert leaked == 0


async def test_arrivals_are_counted_by_where_they_came_from():
    if not await _db_reachable():
        pytest.skip("no database")
    shared, search = await _count("arrival", "share:quote"), await _count("arrival", "search")
    async with _client() as c:
        # The share marker wins over a stripped or misleading referrer.
        await c.post("/api/v1/beacon", json={"e": "arrival", "ref": "", "s": "quote"}, headers=_reader())
        await c.post("/api/v1/beacon", json={"e": "arrival", "ref": "www.google.co.in"}, headers=_reader())
    assert await _count("arrival", "share:quote") == shared + 1
    assert await _count("arrival", "search") == search + 1


async def test_a_visitor_past_the_days_cap_is_not_counted(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    monkeypatch.setattr(usage, "EVENTS_PER_VISITOR_PER_DAY", 2)
    before = await _count("view", "feed")
    h = _reader()
    async with _client() as c:
        for _ in range(5):
            await c.post("/api/v1/beacon", json={"e": "view", "d": "feed"}, headers=h)
    assert await _count("view", "feed") == before + 2


async def test_nothing_is_counted_while_redis_is_away(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")

    def down():
        raise ConnectionError("redis is away")

    monkeypatch.setattr("api.routes.beacon.get_redis", down)
    before = await _count("view", "trending")
    async with _client() as c:
        assert (await c.post("/api/v1/beacon", json={"e": "view", "d": "trending"}, headers=_reader())).status_code == 204
    assert await _count("view", "trending") == before


async def test_a_signed_in_beacon_records_the_day_and_nothing_else():
    if not await _db_reachable():
        pytest.skip("no database")
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": f"r-{uid.hex[:8]}@example.test"})
        bearer = await auth.create_session(s, uid)
    try:
        async with _client() as c:
            for page in ("feed", "story"):
                await c.post("/api/v1/beacon", json={"e": "view", "d": page},
                             headers={**_reader(), "Authorization": f"Bearer {bearer}"})
        async with session_scope() as s:
            days = (await s.execute(text("SELECT day FROM user_days WHERE user_id = :u"), {"u": uid})).scalars().all()
        assert days == [usage.today()]
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sessions WHERE user_id = :u"), {"u": uid})
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})

