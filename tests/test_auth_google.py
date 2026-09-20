"""Google sign-in: the ID token is checked for OUR audience, Google's issuer and
a verified email; the verified email is the identity, shared with magic link."""
import pytest
from httpx import ASGITransport, AsyncClient

import common.auth as auth
from api.main import app
from common.config import get_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _Resp:
    def __init__(self, status, payload):
        self.status_code, self._p = status, payload

    def json(self):
        return self._p


def _tokeninfo(monkeypatch, status=200, **claims):
    class _Client:
        def __init__(self, *a, **k): ...
        async def __aenter__(self): return self
        async def __aexit__(self, *a): return False
        async def get(self, url, params=None): return _Resp(status, claims)

    monkeypatch.setattr("httpx.AsyncClient", _Client)
    monkeypatch.setattr(get_settings(), "google_client_id", "prism-web.apps.googleusercontent.com")


async def test_a_token_minted_for_another_app_is_refused(monkeypatch):
    _tokeninfo(monkeypatch, aud="someone-else", iss="accounts.google.com", email="a@b.c", email_verified="true")
    with pytest.raises(auth.GoogleTokenInvalid):
        await auth.verify_google_id_token("x")


async def test_an_unverified_email_is_refused(monkeypatch):
    _tokeninfo(monkeypatch, aud="prism-web.apps.googleusercontent.com", iss="accounts.google.com", email="a@b.c", email_verified="false")
    with pytest.raises(auth.GoogleTokenInvalid):
        await auth.verify_google_id_token("x")


async def test_a_good_token_yields_the_email(monkeypatch):
    _tokeninfo(monkeypatch, aud="prism-web.apps.googleusercontent.com", iss="https://accounts.google.com", email="Reader@Example.com", email_verified="true")
    assert await auth.verify_google_id_token("x") == "Reader@Example.com"


async def test_the_route_returns_the_same_session_shape_as_magic_link(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    _tokeninfo(monkeypatch, aud="prism-web.apps.googleusercontent.com", iss="accounts.google.com", email="google-signin@t.test", email_verified="true")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v1/auth/google", json={"credential": "x"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert set(body) >= {"token", "user_id", "email", "needs_profile"} and body["email"] == "google-signin@t.test"
    from sqlalchemy import text

    from common.db import session_scope
    async with session_scope() as s:
        await s.execute(text("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email = 'google-signin@t.test')"))
        await s.execute(text("DELETE FROM usage_quota WHERE user_id IN (SELECT id FROM users WHERE email = 'google-signin@t.test')"))
        await s.execute(text("DELETE FROM users WHERE email = 'google-signin@t.test'"))


async def _db() -> bool:
    try:
        from sqlalchemy import text

        from common.db import session_scope
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False
