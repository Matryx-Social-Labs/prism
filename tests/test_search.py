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


# --- the index that keeps this route off a full table scan ----------------------
# Measured on production before migration c8a3f5d21b74: Seq Scan, ~100ms per query
# over 19,356 events, growing linearly. The route's leading-wildcard ILIKE cannot
# use a btree, so it needs GIN over trigrams.
#
# This asserts the SCHEMA rather than a query plan on purpose. The local test
# database holds a couple of hundred rows, where Postgres correctly prefers a
# sequential scan whatever indexes exist — so an EXPLAIN assertion here would fail
# for a reason that has nothing to do with the thing being tested.


async def test_search_columns_have_trigram_indexes():
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        rows = await s.execute(
            text(
                "SELECT indexdef FROM pg_indexes "
                "WHERE tablename = 'events' AND indexdef ILIKE '%gin_trgm_ops%'"
            )
        )
        defs = " ".join(r[0] for r in rows.all())
    assert "title" in defs, "events.title has no trigram index; search full-scans"
    assert "summary" in defs, "events.summary has no trigram index; search full-scans"


async def test_search_still_matches_inside_a_word():
    """Substring semantics are the reason this used ILIKE and not tsvector. A
    lexeme index would quietly stop matching mid-word, which is a product change,
    not a performance one — so it is pinned here."""
    if not await _db_reachable():
        pytest.skip("no database")
    token = uuid.uuid4().hex[:10]
    await _seed(f"Prefix{token}Suffix headline", "body", "politics")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as client:
        r = await client.get("/api/v1/search", params={"q": token})
    assert r.status_code == 200
    assert any(token in i["title"] for i in r.json()["items"]), (
        "a mid-word substring stopped matching — search semantics changed"
    )
