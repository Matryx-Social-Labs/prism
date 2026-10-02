"""A founder's pin on /trending (api/routes/admin_stories.py): a pinned story
leads the list, ahead of the running stories, and stays listed while the pin
holds even after it goes quiet. Only a founder pins; each pin and unpin is in
the audit log."""

import uuid

import pytest
from sqlalchemy import text

from common.db import session_scope
from tests.test_share_links import _cleanup, _client, _founder
from tests.test_verified_tier import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _story(s, slug: str, *, status: str, scope: str | None = None, velocity: int = 0) -> uuid.UUID:
    sid, ev = uuid.uuid4(), uuid.uuid4()
    await s.execute(text("INSERT INTO events (id, title, sector) VALUES (:i, :t, 'other')"), {"i": str(ev), "t": slug})
    await s.execute(text("INSERT INTO stories (id, slug, label, \"cast\", member_event_ids, hero_event_id, anchor_event_id, "
                         "scope, source_count, velocity, status) VALUES (:i, :sl, :sl, '[]'::jsonb, CAST(:m AS jsonb), "
                         ":e, :e, :sc, 3, :v, :st)"),
                    {"i": str(sid), "sl": slug, "m": f'["{ev}", "{uuid.uuid4()}"]', "e": str(ev), "sc": scope,
                     "v": velocity, "st": status})
    return sid


async def test_a_founder_pins_a_quiet_story_to_the_head_of_the_list_and_unpins_it(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    h, reader, users = await _founder(tag, monkeypatch)
    quiet, war, hot = f"quiet-{tag}", f"war-{tag}", f"hot-{tag}"
    async with session_scope() as s:
        ids = [await _story(s, quiet, status="dormant"), await _story(s, war, status="active", scope="A war"),
               await _story(s, hot, status="active", velocity=99)]
    try:
        async with _client() as c:
            async def order():
                return [x["slug"] for x in (await c.get("/api/v1/trending?limit=50")).json()["stories"]]

            assert quiet not in await order(), "a quiet story is not listed"
            for method in ("POST", "DELETE"):
                assert (await c.request(method, f"/api/v1/admin/stories/{quiet}/pin", json={"days": 3})).status_code == 401
                assert (await c.request(method, f"/api/v1/admin/stories/{quiet}/pin", json={"days": 3},
                                        headers=reader)).status_code == 403
            assert (await c.post(f"/api/v1/admin/stories/{quiet}/pin", json={"days": 99}, headers=h)).status_code == 422
            assert (await c.post(f"/api/v1/admin/stories/nothing-{tag}/pin", json={"days": 3}, headers=h)).status_code == 404
            r = await c.post(f"/api/v1/admin/stories/{quiet}/pin", json={"days": 3}, headers=h)
            assert r.status_code == 200 and r.json()["pinned"] is True
            listed = (await c.get("/api/v1/trending?limit=50")).json()["stories"]
            slugs = [x["slug"] for x in listed]
            assert slugs.index(quiet) < slugs.index(war) < slugs.index(hot), "pinned, then running, then the heat"
            assert next(x for x in listed if x["slug"] == quiet)["pinned"] is True
            admin = (await c.get("/api/v1/admin/stories", headers=h)).json()["stories"]
            assert admin[0]["slug"] == quiet or any(x["slug"] == quiet and x["pinned"] for x in admin)
            assert (await c.delete(f"/api/v1/admin/stories/{quiet}/pin", headers=h)).json()["pinned"] is False
            assert quiet not in await order()
        async with session_scope() as s:
            audited = (await s.execute(text("SELECT action FROM admin_audit WHERE actor = :a AND target = :t ORDER BY id"),
                                       {"a": f"founder-{tag}@example.test", "t": quiet})).scalars().all()
        assert audited == ["story.pin", "story.unpin"]
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"), {"i": [str(i) for i in ids]})
            await s.execute(text("DELETE FROM events WHERE title = ANY(:t)"), {"t": [quiet, war, hot]})
        await _cleanup(tag, users)
