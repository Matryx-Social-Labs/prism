"""People, switches and the collection trigger on /admin (plan phase D).

Pinned: only a founder reads or acts; the people list carries each account's
plan, activity and labelling; the switches are exactly the listed ones, as the
API sees them, and never a string setting; and a trigger is published and
recorded against the founder who pressed it.
"""

import uuid
from datetime import timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from api.routes import admin_controls
from common import auth, usage
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


async def test_people_flags_and_trigger_are_a_founders_alone(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    founder, reader = uuid.uuid4(), uuid.uuid4()
    published = []

    async def publish(topic, message):
        published.append((topic, message))
        return "1-0"

    monkeypatch.setattr(admin_controls.stream, "publish", publish)
    monkeypatch.setattr(get_settings(), "prism_admin_emails", f"founder-{tag}@example.test")
    async with session_scope() as s:
        for uid, who in ((founder, "founder"), (reader, "reader")):
            await s.execute(text("INSERT INTO users (id, email, profession, languages) VALUES (:i, :e, 'journalist', ARRAY['kn'])"),
                            {"i": uid, "e": f"{who}-{tag}@example.test"})
        await s.execute(text("INSERT INTO labellers (user_id, languages_read, status) VALUES (:u, ARRAY['kn'], 'applied')"), {"u": reader})
        await s.execute(text("INSERT INTO subscriptions (id, user_id, provider, plan, status, price_paise) "
                             "VALUES (:i, :u, 'razorpay', 'plus_monthly', 'active', 14900)"), {"i": uuid.uuid4(), "u": reader})
        for back in (0, 3, 40):  # the last one is outside the 28-day window
            await s.execute(text("INSERT INTO user_days (user_id, day) VALUES (:u, :d)"),
                            {"u": reader, "d": usage.today() - timedelta(days=back)})
        fb = await auth.create_session(s, founder)
        rb = await auth.create_session(s, reader)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            for method, path in (("GET", "/api/v1/admin/people"), ("GET", "/api/v1/admin/flags"),
                                 ("POST", "/api/v1/admin/pipeline/trigger")):
                assert (await c.request(method, path)).status_code == 401
                assert (await c.request(method, path, headers={"Authorization": f"Bearer {rb}"})).status_code == 403
            assert published == [], "a refused trigger must not reach the worker"
            h = {"Authorization": f"Bearer {fb}"}

            r = await c.get("/api/v1/admin/people?limit=500", headers=h)
            me = next(p for p in r.json()["people"] if p["email"] == f"reader-{tag}@example.test")
            assert (me["plan"], me["plan_status"], me["labeller"]) == ("plus_monthly", "active", "applied")
            assert me["active_days"] == 2 and me["languages"] == ["kn"]

            r = await c.get("/api/v1/admin/flags", headers=h)
            shown = {f["name"]: f["value"] for f in r.json()["flags"]}
            assert set(shown) == {n.upper() for n in admin_controls.FLAGS}
            assert shown["PRISM_INGESTION_ENABLED"] == get_settings().prism_ingestion_enabled
            assert all(not isinstance(v, str) for v in shown.values()), "a string setting could be a secret"
            assert "PRISM_ADMIN_TOKEN" not in shown

            r = await c.post("/api/v1/admin/pipeline/trigger", headers=h)
            assert r.status_code == 200
        assert published == [("admin.triggers", {"requested_by": f"founder-{tag}@example.test"})]
        async with session_scope() as s:
            actors = (await s.execute(text("SELECT actor FROM admin_audit WHERE action = 'pipeline.run' AND actor = :a"),
                                      {"a": f"founder-{tag}@example.test"})).scalars().all()
        assert actors == [f"founder-{tag}@example.test"]
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM admin_audit WHERE actor = :a"), {"a": f"founder-{tag}@example.test"})
            await s.execute(text("DELETE FROM subscriptions WHERE user_id = :u"), {"u": reader})
            await s.execute(text("DELETE FROM sessions WHERE user_id = ANY(:u)"), {"u": [founder, reader]})
            await s.execute(text("DELETE FROM users WHERE id = ANY(:u)"), {"u": [founder, reader]})
