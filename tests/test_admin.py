"""The /admin dashboard's guard (founder decision D1, 2026-09-23).

Only a signed-in account whose email is on PRISM_ADMIN_EMAILS gets in; an
empty list lets nobody in; and every change the dashboard makes leaves a row
in admin_audit naming the founder who made it.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import auth
from common.admin_audit import audit
from common.config import get_settings
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _account(email: str) -> tuple[uuid.UUID, str]:
    uid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO users (id, email) VALUES (:i, :e)"), {"i": uid, "e": email})
        bearer = await auth.create_session(s, uid)
    return uid, bearer


async def _cleanup(*uids: uuid.UUID) -> None:
    async with session_scope() as s:
        for uid in uids:
            await s.execute(text("DELETE FROM sessions WHERE user_id = :u"), {"u": uid})
            await s.execute(text("DELETE FROM users WHERE id = :u"), {"u": uid})


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


@pytest.fixture
def admins(monkeypatch):
    def set_(value: str) -> None:
        monkeypatch.setattr(get_settings(), "prism_admin_emails", value)
    return set_


async def test_only_a_listed_account_gets_in(admins):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder, founder_bearer = await _account(f"Founder-{tag}@Example.test")
    reader, reader_bearer = await _account(f"reader-{tag}@example.test")
    # Case and spacing in the variable must not matter, and neither must the
    # case the account was created with.
    admins(f" someone@else.test , founder-{tag}@example.TEST ")
    try:
        async with _client() as c:
            assert (await c.get("/api/v1/admin/me")).status_code == 401
            r = await c.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {reader_bearer}"})
            assert r.status_code == 403
            r = await c.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {founder_bearer}"})
            assert r.status_code == 200 and r.json() == {"email": f"founder-{tag}@example.test"}
            # The audit log is behind the same guard.
            r = await c.get("/api/v1/admin/audit", headers={"Authorization": f"Bearer {reader_bearer}"})
            assert r.status_code == 403
    finally:
        await _cleanup(founder, reader)


async def test_an_empty_list_lets_nobody_in(admins):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    uid, bearer = await _account(f"founder-{tag}@example.test")
    admins("")
    try:
        async with _client() as c:
            r = await c.get("/api/v1/admin/me", headers={"Authorization": f"Bearer {bearer}"})
            assert r.status_code == 403
    finally:
        await _cleanup(uid)


async def test_a_change_is_recorded_against_the_founder_who_made_it(admins):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    uid, bearer = await _account(f"founder-{tag}@example.test")
    admins(f"founder-{tag}@example.test")
    target = f"labeller:test-{tag}"
    try:
        async with session_scope() as s:
            await audit(s, f"founder-{tag}@example.test", "approve", target, {"from": "applied"})
        async with _client() as c:
            r = await c.get("/api/v1/admin/audit", headers={"Authorization": f"Bearer {bearer}"})
        assert r.status_code == 200
        mine = [e for e in r.json()["entries"] if e["target"] == target]
        assert mine and mine[0]["actor"] == f"founder-{tag}@example.test"
        assert mine[0]["action"] == "approve" and mine[0]["detail"] == {"from": "applied"}
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM admin_audit WHERE target = :t"), {"t": target})
        await _cleanup(uid)
