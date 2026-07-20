"""Sign-up profiling: professions vocabulary, mandatory name/profession, and the
profile carried through the magic-link flow onto a new user.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
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


async def _cleanup(email: str) -> None:
    async with session_scope() as s:
        ids = (await s.execute(text("SELECT id FROM users WHERE email = :e"), {"e": email})).scalars().all()
        for t in ("usage_quota", "sessions", "watchlist"):
            await s.execute(text(f"DELETE FROM {t} WHERE user_id = ANY(:ids)"), {"ids": [str(i) for i in ids]})
        await s.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})
        await s.execute(text("DELETE FROM auth_tokens WHERE email = :e"), {"e": email})


async def test_professions_endpoint_and_signup_validation():
    if not await _db_reachable():
        pytest.skip("no database")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://t") as ac:
        groups = (await ac.get("/api/v1/professions")).json()["groups"]
        assert groups and all("group" in g and g["options"] for g in groups)
        slug = groups[0]["options"][0]["slug"]

        base = {"email": "x@example.com", "consent": True}
        assert (await ac.post("/api/v1/auth/request", json=base)).status_code == 422  # no name
        assert (await ac.post("/api/v1/auth/request", json={**base, "name": "A"})).status_code == 422  # no profession
        assert (
            await ac.post("/api/v1/auth/request", json={**base, "name": "A", "profession": "not_a_slug"})
        ).status_code == 422  # bad profession
        ok = await ac.post("/api/v1/auth/request", json={**base, "name": "A", "profession": slug})
        assert ok.status_code == 200
    await _cleanup("x@example.com")


async def test_profile_lands_on_new_user():
    if not await _db_reachable():
        pytest.skip("no database")
    email = f"prof-{uuid.uuid4().hex[:8]}@example.com"
    try:
        async with session_scope() as s:
            raw = await auth.request_magic_link(s, email, name="Ada Lovelace", profession="security_analyst")
        async with session_scope() as s:
            uid = await auth.verify_and_consume(s, raw)
        async with session_scope() as s:
            row = (
                await s.execute(text("SELECT name, profession FROM users WHERE id = :i"), {"i": str(uid)})
            ).mappings().first()
        assert row["name"] == "Ada Lovelace" and row["profession"] == "security_analyst"
    finally:
        await _cleanup(email)
