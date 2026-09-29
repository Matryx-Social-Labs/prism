"""A new free account gets one welcome, on its first verify, and never again.

A service message (docs/COMPLIANCE-INDIA.md: no marketing without opt-in): what
the account adds, counted from common/quota.py rather than typed; where to pick
subjects; how to delete the account; the week's record named only as off.
"""

import uuid
from types import SimpleNamespace

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

import api.routes.auth as auth_routes
from common import auth
from common.config import get_settings
from common.db import session_scope
from common.email_templates import welcome_email
from common.quota import USER_ASK_PER_DAY, USER_LENS_PER_DAY
from tests.test_projection_summary import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _Sender:
    def __init__(self):
        self.sent = []

    async def send(self, *, to, subject, body, html=None, reply_to=None, headers=None):
        self.sent.append(SimpleNamespace(to=to, subject=subject, body=body, html=html))


def _client():
    from api.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="https://t")


async def _link(email: str) -> str:
    async with session_scope() as s:
        await s.execute(text("DELETE FROM auth_tokens WHERE email = :e"), {"e": email})  # past the cooldown
        return await auth.request_magic_link(s, email)


async def _cleanup(email: str):
    async with session_scope() as s:
        for t in ("usage_quota", "sessions"):
            await s.execute(text(f"DELETE FROM {t} WHERE user_id IN (SELECT id FROM users WHERE email=:e)"), {"e": email})
        await s.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
        await s.execute(text("DELETE FROM auth_tokens WHERE email=:e"), {"e": email})


async def test_the_welcome_is_a_service_message_counted_from_the_quota():
    body, html = welcome_email(to="r@example.com")
    assert f"{USER_LENS_PER_DAY} lens readings and {USER_ASK_PER_DAY} questions a day, and a watchlist" in body
    assert f"{get_settings().prism_web_url.rstrip('/')}/interests" in html
    assert "delete your account" in body and "hello@readprism.news" in body
    assert "week's record by email is off" in body
    assert "AI-powered" not in body and "Plus" not in body, "no marketing in a service message"


async def test_a_new_account_is_welcomed_once_and_a_later_sign_in_is_not(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    sender = _Sender()
    monkeypatch.setattr(auth_routes, "get_email_sender", lambda: sender)
    email = f"welcome-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with _client() as c:
            assert (await c.post("/api/v1/auth/verify", json={"token": await _link(email)})).status_code == 200
            assert [(m.to, m.subject) for m in sender.sent] == [(email, "Your Prism account")]
            # Signing in again, by link or by Google on the same address: the same account, no second welcome.
            assert (await c.post("/api/v1/auth/verify", json={"token": await _link(email)})).status_code == 200

            async def _google(_token):
                return email.upper()

            monkeypatch.setattr(auth, "verify_google_access_token", _google)
            assert (await c.post("/api/v1/auth/google", json={"access_token": "t"})).status_code == 200
        assert len(sender.sent) == 1
    finally:
        await _cleanup(email)


async def test_a_new_account_by_google_is_welcomed_too(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    sender = _Sender()
    monkeypatch.setattr(auth_routes, "get_email_sender", lambda: sender)
    email = f"welcome-g-{uuid.uuid4().hex[:8]}@example.com"

    async def _google(_token):
        return email

    monkeypatch.setattr(auth, "verify_google_access_token", _google)
    try:
        async with _client() as c:
            assert (await c.post("/api/v1/auth/google", json={"access_token": "t"})).status_code == 200
        assert [m.to for m in sender.sent] == [email]
    finally:
        await _cleanup(email)


async def test_a_dropped_welcome_never_fails_the_sign_in(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")

    class _Down:
        async def send(self, **_):
            raise RuntimeError("resend send failed (503)")

    monkeypatch.setattr(auth_routes, "get_email_sender", lambda: _Down())
    email = f"welcome-d-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with _client() as c:
            r = await c.post("/api/v1/auth/verify", json={"token": await _link(email)})
            assert r.status_code == 200 and r.json()["email"] == email
            assert (await c.get("/api/v1/auth/me")).status_code == 200
    finally:
        await _cleanup(email)
