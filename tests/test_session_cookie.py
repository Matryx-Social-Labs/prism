"""The session travels in an HttpOnly cookie, never in storage a script can read.

Audit C5: the 30-day bearer token sat in localStorage, where any injected script
could read it. Now sign-in sets it as an HttpOnly, Secure, SameSite=Lax cookie
and the page never holds it. Pinned: the cookie's flags; that it authenticates
on its own; that a write it would authenticate from another site's page is
refused while the same write from ours is not; that signing out kills the
session AND the cookie; that a page signed in before the cookie can adopt it;
and that the header still works for tools and pages mid-migration.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from common import auth
from common.db import session_scope
from tests.test_projection_summary import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")

OURS = "http://localhost:3000"  # in cors_origin_list by default
THEIRS = "https://evil.example"
PROFILE = {"name": "Asha", "profession": "tech_founder", "state": "IN-KA", "languages": ["en"], "consent": True}


def _client():
    from api.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="https://t")


async def _signed_in(c: AsyncClient, email: str):
    async with session_scope() as s:
        raw = await auth.request_magic_link(s, email)
    return await c.post("/api/v1/auth/verify", json={"token": raw})


async def _cleanup(email: str):
    async with session_scope() as s:
        for t in ("usage_quota", "sessions"):
            await s.execute(text(f"DELETE FROM {t} WHERE user_id IN (SELECT id FROM users WHERE email=:e)"), {"e": email})
        await s.execute(text("DELETE FROM users WHERE email=:e"), {"e": email})
        await s.execute(text("DELETE FROM auth_tokens WHERE email=:e"), {"e": email})


async def test_sign_in_sets_an_httponly_cookie_that_authenticates_on_its_own():
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"c-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with _client() as c:
            r = await _signed_in(c, email)
            assert r.status_code == 200, r.text
            assert "token" not in r.json(), "a credential handed to page script is what C5 retired"
            header = r.headers["set-cookie"].lower()
            assert "prism_session=" in header and "httponly" in header and "samesite=lax" in header
            assert "secure" in header and "max-age=2592000" in header
            # The cookie alone (the client keeps it), no Authorization header.
            me = await c.get("/api/v1/auth/me")
            assert me.status_code == 200 and me.json()["email"] == email
    finally:
        await _cleanup(email)


async def test_a_cookie_write_from_another_sites_page_is_refused_and_ours_is_not():
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"c-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with _client() as c:
            await _signed_in(c, email)
            theirs = await c.post("/api/v1/auth/profile", json=PROFILE, headers={"Origin": THEIRS})
            assert theirs.status_code == 401, "another site's page must not write with our cookie"
            ours = await c.post("/api/v1/auth/profile", json=PROFILE, headers={"Origin": OURS})
            assert ours.status_code == 200, ours.text
    finally:
        await _cleanup(email)


async def test_signing_out_kills_the_session_and_the_cookie():
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"c-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with _client() as c:
            await _signed_in(c, email)
            token = c.cookies.get("prism_session")
            out = await c.delete("/api/v1/auth/session", headers={"Origin": OURS})
            assert out.status_code == 204
            assert "max-age=0" in out.headers["set-cookie"].lower()
        async with _client() as c:
            # The token itself is dead, not merely forgotten by the browser.
            assert (await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 401
    finally:
        await _cleanup(email)


async def test_a_page_signed_in_before_the_cookie_adopts_it_and_the_header_still_works():
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"c-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with _client() as c:
            await _signed_in(c, email)
            token = c.cookies.get("prism_session")
        async with _client() as c:  # a fresh browser that only has the stored token
            assert (await c.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})).status_code == 200
            adopted = await c.post("/api/v1/auth/cookie", headers={"Authorization": f"Bearer {token}", "Origin": OURS})
            assert adopted.status_code == 204 and "httponly" in adopted.headers["set-cookie"].lower()
            assert (await c.get("/api/v1/auth/me")).status_code == 200
            dead = await c.post("/api/v1/auth/cookie", headers={"Authorization": "Bearer not-a-session"})
            assert dead.status_code == 401
    finally:
        await _cleanup(email)
