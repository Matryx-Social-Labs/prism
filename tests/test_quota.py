"""Atomic sample-quota checks (freemium D4 — the cost wall).

The load-bearing property: N concurrent consumers of the same account's quota
must together consume at most `remaining` samples, never more. If this can
double-spend, on-demand LLM generation goes unbounded — the whole reason the
paywall exists. Runs against a live Postgres (docker compose up postgres);
skips cleanly when no DB is reachable so `pytest` stays green without one.
"""

import asyncio
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from common.quota import grant_samples, remaining_samples, try_consume_sample

# common.db memoizes one async engine; its pool binds to the loop that first
# used it. Share one loop across this module's tests so that engine stays valid
# (otherwise a later test on a fresh loop hits "Event loop is closed").
pytestmark = pytest.mark.asyncio(loop_scope="module")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _make_user(email: str) -> uuid.UUID:
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO users (id, email) VALUES (:id, :email)"),
            {"id": str(uid), "email": email},
        )
    return uid


async def _cleanup(uid: uuid.UUID) -> None:
    async with session_scope() as s:
        await s.execute(text("DELETE FROM usage_quota WHERE user_id = :u"), {"u": str(uid)})
        await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": str(uid)})


async def test_atomic_quota_never_double_spends():
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres` to exercise this")

    uid = await _make_user(f"race-{uuid.uuid4()}@example.com")
    try:
        async with session_scope() as s:
            await grant_samples(s, uid, 5)

        # 25 concurrent consumers, each in its own transaction, race the one row.
        async def consume() -> bool:
            async with session_scope() as s:
                return await try_consume_sample(s, uid)

        results = await asyncio.gather(*[consume() for _ in range(25)])

        assert sum(results) == 5, f"expected exactly 5 successes, got {sum(results)}"
        async with session_scope() as s:
            assert await remaining_samples(s, uid) == 0
    finally:
        await _cleanup(uid)


async def test_consume_on_missing_quota_returns_false():
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres` to exercise this")

    uid = await _make_user(f"noquota-{uuid.uuid4()}@example.com")
    try:
        async with session_scope() as s:
            assert await try_consume_sample(s, uid) is False  # no row → no spend
    finally:
        await _cleanup(uid)
