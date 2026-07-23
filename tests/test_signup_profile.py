"""Onboarding vocabulary + the email-first request contract at the HTTP layer.

The function-level auth flow (verify → profile) is covered in test_auth_flow.py;
this locks the HTTP endpoints: professions + languages pickers, and that
/auth/request is email-only and enumeration-safe (same 200 for any email).
"""

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


async def test_professions_and_languages_endpoints():
    if not await _db_reachable():
        pytest.skip("no database")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        groups = (await ac.get("/api/v1/professions")).json()["groups"]
        assert groups and all("group" in g and g["options"] for g in groups)

        body = (await ac.get("/api/v1/languages")).json()
        codes = {lg["code"] for lg in body["languages"]}
        assert {"en", "hi", "kn"} <= codes  # Bangalore launch set
        # Native-script labels so a reader recognises their own language.
        native = {lg["code"]: lg["native"] for lg in body["languages"]}
        assert native["hi"] == "हिन्दी" and native["kn"] == "ಕನ್ನಡ"
        assert body["default"]  # a sensible pre-selection


async def test_auth_request_is_email_only_and_enumeration_safe():
    if not await _db_reachable():
        pytest.skip("no database")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        # Email-only — no name/profession/consent required to send the link.
        r = await ac.post("/api/v1/auth/request", json={"email": "someone@example.com"})
        assert r.status_code == 200
        # A bad email is rejected...
        assert (await ac.post("/api/v1/auth/request", json={"email": "notanemail"})).status_code == 422
        # ...but the same email again returns 200 (rate-limited internally) — the
        # response never reveals whether the account exists.
        r2 = await ac.post("/api/v1/auth/request", json={"email": "someone@example.com"})
        assert r2.status_code == 200
    async with session_scope() as s:
        await s.execute(text("DELETE FROM auth_tokens WHERE email = :e"), {"e": "someone@example.com"})
