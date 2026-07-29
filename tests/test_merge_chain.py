"""A shared storyline link must land on the live story, however many merges deep.

The route followed exactly ONE hop, on the stated assumption that "merges always
point at a canonical". An audit on 2026-07-28 found a two-hop chain among 356
merged rows, so that link resolved to a story that was itself merged — dormant,
superseded, not what the reader should see.
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


async def _story(s, sid, slug, *, merged_into=None, label="A story"):
    # status computed here rather than in SQL: a bare :mi used twice (once in a
    # CASE, once cast to uuid) leaves asyncpg unable to infer the parameter type.
    await s.execute(
        text('INSERT INTO stories (id, slug, label, "cast", member_event_ids, sector, '
             "source_count, velocity, status, merged_into) "
             "VALUES (:i,:sl,:lb,'[]'::jsonb,'[]'::jsonb,'politics',1,0,:st,CAST(:mi AS uuid))"),
        {
            "i": str(sid), "sl": slug, "lb": label,
            "st": "dormant" if merged_into else "current",
            "mi": str(merged_into) if merged_into else None,
        },
    )


async def _get(slug):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as c:
        return await c.get(f"/api/v1/trending/{slug}")


async def test_a_two_hop_merge_lands_on_the_live_story():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    a, b, c = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    try:
        async with session_scope() as s:
            await _story(s, c, f"live-{tag}", label="The live story")
            await _story(s, b, f"mid-{tag}", merged_into=c)
            await _story(s, a, f"old-{tag}", merged_into=b)

        r = await _get(f"old-{tag}")
        assert r.status_code == 200
        body = r.json()
        story = body.get("story", body)
        assert story["label"] == "The live story", (
            f"one-hop landed on a merged story instead: {story['label']!r}"
        )
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(a), str(b), str(c)]})


async def test_a_single_hop_still_works():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    a, b = uuid.uuid4(), uuid.uuid4()
    try:
        async with session_scope() as s:
            await _story(s, b, f"canon-{tag}", label="Canonical")
            await _story(s, a, f"shared-{tag}", merged_into=b)
        r = await _get(f"shared-{tag}")
        assert r.status_code == 200
        story = r.json().get("story", r.json())
        assert story["label"] == "Canonical"
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(a), str(b)]})


async def test_a_merge_cycle_fails_loudly_instead_of_hanging():
    """A `while` here would spin the request thread forever on corrupt data."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    a, b = uuid.uuid4(), uuid.uuid4()
    try:
        async with session_scope() as s:
            await _story(s, a, f"cyc-a-{tag}")
            await _story(s, b, f"cyc-b-{tag}", merged_into=a)
            await s.execute(text("UPDATE stories SET merged_into = :b WHERE id = :a"),
                            {"b": str(b), "a": str(a)})
        r = await _get(f"cyc-a-{tag}")
        assert r.status_code == 500
    finally:
        async with session_scope() as s:
            await s.execute(text("UPDATE stories SET merged_into = NULL WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(a), str(b)]})
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(a), str(b)]})
