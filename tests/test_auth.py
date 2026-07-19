"""Magic-link auth: full flow + the security edges (N3).

Runs against a live Postgres; skips cleanly when none is reachable. Exercises
the logic layer directly (common/auth.py) so no HTTP/event-loop machinery is
involved. Proves: raw tokens are never stored, magic tokens are single-use and
expiry-bound, sessions resolve, and requests are rate-limited.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common import auth
from common.db import get_db, session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _cleanup(email: str) -> None:
    async with session_scope() as s:
        await s.execute(
            text(
                "DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email = :e)"
            ),
            {"e": email},
        )
        await s.execute(
            text(
                "DELETE FROM usage_quota WHERE user_id IN (SELECT id FROM users WHERE email = :e)"
            ),
            {"e": email},
        )
        await s.execute(text("DELETE FROM auth_tokens WHERE email = :e"), {"e": email})
        await s.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})


async def test_full_magic_link_flow_and_single_use():
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres`")
    email = f"flow-{uuid.uuid4()}@example.com"
    try:
        async with session_scope() as s:
            raw = await auth.request_magic_link(s, email)
        assert raw and len(raw) > 20

        # Raw token is never stored — only its hash.
        async with session_scope() as s:
            stored = (
                await s.execute(
                    text("SELECT token_hash FROM auth_tokens WHERE email = :e"), {"e": email}
                )
            ).scalar_one()
        assert stored != raw and stored == auth._hash(raw)

        # First verify: creates the user, grants samples, returns a user id.
        async with session_scope() as s:
            user_id = await auth.verify_and_consume(s, raw)
        assert user_id is not None
        async with session_scope() as s:
            samples = (
                await s.execute(
                    text("SELECT remaining FROM usage_quota WHERE user_id = :u"),
                    {"u": str(user_id)},
                )
            ).scalar_one_or_none()
        assert samples == 3  # prism_free_markets_samples default

        # Single-use: the same token can't be redeemed twice.
        async with session_scope() as s:
            assert await auth.verify_and_consume(s, raw) is None

        # A session resolves; a garbage bearer does not.
        async with session_scope() as s:
            bearer = await auth.create_session(s, user_id)
        async with session_scope() as s:
            assert await auth.resolve_session(s, bearer) == user_id
            assert await auth.resolve_session(s, "not-a-real-token") is None
    finally:
        await _cleanup(email)


async def test_expired_and_unknown_tokens_rejected():
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres`")
    email = f"exp-{uuid.uuid4()}@example.com"
    try:
        raw = "expired-token-raw"
        async with session_scope() as s:
            await s.execute(
                text(
                    "INSERT INTO auth_tokens (id, email, token_hash, expires_at) "
                    "VALUES (gen_random_uuid(), :e, :h, now() - interval '1 minute')"
                ),
                {"e": email, "h": auth._hash(raw)},
            )
        async with session_scope() as s:
            assert await auth.verify_and_consume(s, raw) is None  # expired
            assert await auth.verify_and_consume(s, "never-issued") is None  # unknown
    finally:
        await _cleanup(email)


async def test_request_is_rate_limited():
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres`")
    email = f"rate-{uuid.uuid4()}@example.com"
    try:
        async with session_scope() as s:
            await auth.request_magic_link(s, email)
        async with session_scope() as s:
            with pytest.raises(auth.RateLimited):
                await auth.request_magic_link(s, email)
    finally:
        await _cleanup(email)


async def test_get_db_commits_writes():
    """Regression: the FastAPI get_db dependency must commit on success, or every
    write endpoint (auth, the paywall gate, watchlist) silently rolls back. This
    is what broke the magic-link flow over HTTP while the logic-level tests passed.
    """
    if not await _db_reachable():
        pytest.skip("no database — run `docker compose up -d postgres`")
    email = f"getdb-{uuid.uuid4()}@example.com"
    try:
        # Drive get_db like FastAPI does: take the session, write, then exhaust
        # the generator so its `async with` exits and commits.
        gen = get_db()
        s = await gen.__anext__()
        await s.execute(
            text("INSERT INTO users (id, email) VALUES (gen_random_uuid(), :e)"), {"e": email}
        )
        with pytest.raises(StopAsyncIteration):
            await gen.__anext__()
        # A separate session must see the committed row.
        async with session_scope() as s2:
            assert (
                await s2.execute(text("SELECT 1 FROM users WHERE email = :e"), {"e": email})
            ).scalar_one_or_none() == 1
    finally:
        await _cleanup(email)
