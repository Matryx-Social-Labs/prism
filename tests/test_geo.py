"""Geo: the regions vocabulary + the feed's state-first tiering.

Seeds two India events (one in-state, one national) and asserts the reader's
state surfaces first even when the national one is newer.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed_event(title: str, sector: str, regions: list[str], newer: bool) -> uuid.UUID:
    eid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text(
                "INSERT INTO events (id, title, summary, sector, regions, last_updated_at, projection) "
                "VALUES (:i, :t, :t, :sec, CAST(:r AS text[]), "
                "now() - make_interval(mins => :age), '{}'::jsonb)"
            ),
            {"i": str(eid), "t": title, "sec": sector, "r": regions, "age": 1 if newer else 120},
        )
    return eid


async def test_regions_endpoint():
    if not await _db_reachable():
        pytest.skip("no database")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        body = (await ac.get("/api/v1/regions")).json()
    assert body["country"] == "IN"
    codes = {s["code"] for s in body["states"]}
    assert {"IN-KA", "IN-TN", "IN-MH"} <= codes
    assert any(s["covered"] for s in body["states"])  # some states have local sources


async def test_feed_state_tiering():
    if not await _db_reachable():
        pytest.skip("no database")
    # national event is NEWER, so recency alone would rank it first — tiering must
    # still surface the in-state event ahead of it.
    e_state = await _seed_event("State assembly passes bill", "politics", ["IN", "IN-KA"], newer=False)
    e_nat = await _seed_event("National budget session begins", "politics", ["IN"], newer=True)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            items = (await ac.get("/api/v1/feed", params={"lens": "general", "state": "IN-KA", "limit": 100})).json()["items"]
        by_id = {i["id"]: i for i in items}
        assert str(e_state) in by_id and str(e_nat) in by_id
        assert by_id[str(e_state)]["is_regional"] is True
        assert by_id[str(e_nat)]["is_regional"] is False
        order = [i["id"] for i in items]
        assert order.index(str(e_state)) < order.index(str(e_nat))  # in-state first despite older
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = ANY(:ids)"), {"ids": [str(e_state), str(e_nat)]})
