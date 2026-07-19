"""Search route over HTTP — keyword match on title/summary, recency order.

Drives the real FastAPI app via httpx/ASGITransport against a live Postgres.
Skips without a database.
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


async def _seed(title: str, summary: str, sector: str) -> uuid.UUID:
    eid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector) VALUES (:i, :t, :s, :sec)"),
            {"i": str(eid), "t": title, "s": summary, "sec": sector},
        )
    return eid


async def test_search_matches_title_and_summary():
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres`")
    tag = uuid.uuid4().hex[:8]
    e_title = await _seed(f"Zephyron-{tag} raises Series B", "Funding news", "business")
    e_summary = await _seed("A quiet day in markets", f"analysts cite Zephyron-{tag} exposure", "finance")
    e_miss = await _seed("Unrelated cricket result", "no keyword here", "sports")
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://t") as ac:
            # too-short query is rejected by validation
            assert (await ac.get("/api/v1/search", params={"q": "a"})).status_code == 422

            got = {i["id"] for i in (await ac.get("/api/v1/search", params={"q": tag})).json()["items"]}
            assert str(e_title) in got  # matched in title
            assert str(e_summary) in got  # matched in summary
            assert str(e_miss) not in got  # no keyword → excluded

            # empty result set is a clean empty list, not an error
            assert (await ac.get("/api/v1/search", params={"q": "zzz-no-such-" + tag})).json()["items"] == []
    finally:
        async with session_scope() as s:
            await s.execute(
                text("DELETE FROM events WHERE id = ANY(:ids)"),
                {"ids": [str(e_title), str(e_summary), str(e_miss)]},
            )
