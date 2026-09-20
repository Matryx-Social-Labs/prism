"""The ticket carries the way to its route.

/events deliberately serves no timeline (one owner: /trending/{slug}). What it
serves is the slug of the canonical story holding the event, so the story page
can ask the owner. Pinned: the slug comes from an UNMERGED story that contains
the event, and an event no story holds gets None rather than a 500.
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

T0 = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)


def _client(story_row):
    import api.routes.events as events
    from api.main import app

    eid = uuid.uuid4()
    seen: list[tuple[str, dict]] = []

    class _R:
        def __init__(self, sql): self.sql = sql
        def mappings(self): return self
        def scalars(self): return self  # the placeholder-photo hashes: none here
        def first(self):
            if "FROM events WHERE id" in self.sql:
                return {"id": eid, "title": "t", "headline_by": None, "summary": "s", "sector": None, "subsector": None,
                        "image_url": None, "regions": [], "occurred_at": None,
                        "last_updated_at": T0, "projection": {}}
            if "FROM stories" in self.sql:
                return story_row
            return None
        def all(self): return []

    class _S:
        async def execute(self, stmt, params=None, *a, **kw):
            seen.append((str(stmt), params or {}))
            return _R(str(stmt))

    async def fake_db():
        yield _S()

    app.dependency_overrides[events.get_db] = fake_db
    return app, eid, seen, lambda: app.dependency_overrides.pop(events.get_db, None)


@pytest.mark.asyncio(loop_scope="session")
async def test_the_canonical_story_slug_rides_on_the_event():
    app, eid, seen, done = _client({"slug": "vmware-auth-bypass"})
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get(f"/api/v1/events/{eid}")
        assert r.status_code == 200, r.text
        assert r.json()["story_slug"] == "vmware-auth-bypass"
        sql, params = next((s, p) for s, p in seen if "FROM stories" in s)
        # Only a story that still IS the story — a merged row points elsewhere.
        assert "merged_into IS NULL" in sql
        # Containment on the frozen member set, the same set /trending/{slug} reads.
        assert "member_event_ids @>" in sql
        assert params["member"] == f'["{eid}"]'
    finally:
        done()


@pytest.mark.asyncio(loop_scope="session")
async def test_an_event_no_story_holds_gets_none_not_a_500():
    app, eid, _seen, done = _client(None)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get(f"/api/v1/events/{eid}")
        assert r.status_code == 200, r.text
        assert r.json()["story_slug"] is None
    finally:
        done()
