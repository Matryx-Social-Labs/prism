"""Email-first auth: send the link on email alone, create the account only on a
verified email, and collect the profile AFTER verify (fixes the old bug where a
returning reader was forced to re-enter name/profession on every sign-in).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common import auth
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def test_email_first_flow_and_profile_after_verify():
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"reader-{uuid.uuid4().hex[:8]}@example.com"
    try:
        # 1. Email-only request — no name/profession needed to send the link.
        async with session_scope() as s:
            raw = await auth.request_magic_link(s, email)
        assert raw

        # 2. Verify creates the account (only now — no unverified rows) and the
        #    profile is INCOMPLETE, so the reader is routed to onboarding.
        async with session_scope() as s:
            user_id = await auth.verify_and_consume(s, raw)
            assert user_id is not None
            assert await auth.profile_complete(s, user_id) is False

        # 3. Complete onboarding: name/profession/state/languages + consent stamp.
        async with session_scope() as s:
            await auth.set_profile(
                s, user_id, name="Sagar", profession="tech_founder",
                state="IN-KA", languages=["kn", "en"],
            )
        async with session_scope() as s:
            assert await auth.profile_complete(s, user_id) is True
            row = (await s.execute(
                text("SELECT name, languages, state, consented_at FROM users WHERE id=:i"),
                {"i": str(user_id)},
            )).mappings().one()
        assert row["name"] == "Sagar"
        assert row["languages"] == ["kn", "en"]  # order preserved (primary first)
        assert row["state"] == "IN-KA"
        assert row["consented_at"] is not None  # consent captured at the profile step
    finally:
        async with session_scope() as s:
            await s.execute(text(
                "DELETE FROM usage_quota WHERE user_id IN (SELECT id FROM users WHERE email=:e)"
            ), {"e": email})
            await s.execute(text(
                "DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email=:e)"
            ), {"e": email})
            await s.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
            await s.execute(text("DELETE FROM auth_tokens WHERE email=:e"), {"e": email})


async def test_returning_reader_needs_no_profile_reprompt():
    """The old bug: a returning reader was forced to re-enter their profile. Now a
    second verify for the same email sees a complete profile."""
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"return-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with session_scope() as s:
            raw = await auth.request_magic_link(s, email)
        async with session_scope() as s:
            uid = await auth.verify_and_consume(s, raw)
            await auth.set_profile(
                s, uid, name="Ada", profession="tech_founder", state=None, languages=["en"]
            )
        # A later sign-in for the same email (clear the prior token so we're past
        # the request cooldown) — profile already complete.
        async with session_scope() as s:
            await s.execute(text("DELETE FROM auth_tokens WHERE email=:e"), {"e": email})
            raw2 = await auth.request_magic_link(s, email)
        async with session_scope() as s:
            uid2 = await auth.verify_and_consume(s, raw2)
            assert uid2 == uid  # same account
            assert await auth.profile_complete(s, uid2) is True  # no re-prompt
    finally:
        async with session_scope() as s:
            await s.execute(text(
                "DELETE FROM usage_quota WHERE user_id IN (SELECT id FROM users WHERE email=:e)"
            ), {"e": email})
            await s.execute(text(
                "DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email=:e)"
            ), {"e": email})
            await s.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
            await s.execute(text("DELETE FROM auth_tokens WHERE email=:e"), {"e": email})
