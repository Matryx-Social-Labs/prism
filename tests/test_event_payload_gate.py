"""The paywall's real boundary is the event payload, and it has TWO kinds of paid content.

`lens_briefs`/`lens_points` are the prose. `projection.cyber`/`projection.finance`
are the FACTS the desktop rail and the mobile lens block render: CVSS, KEV status,
tickers, the catalyst. f230e0d gated the prose. The facts still left with every
payload — and a signed-out reader can select a locked lens (the flip is the upgrade
moment), so the desktop rail showed "CATALYST · REGULATORY_ACTION" for a lens the
reader had not unlocked. Same class as the /questions leak closed in 4bde965.

`available_lenses` is deliberately computed from the UNFILTERED projection: WHICH
lenses exist is public, WHAT they say is not. These tests pin both halves.
"""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient

T0 = datetime(2026, 7, 27, 10, 0, tzinfo=UTC)
PROJECTION = {
    "lens_briefs": {"reader": "free prose", "cyber": "PAID cyber prose", "markets": "PAID markets prose"},
    "lens_points": {"cyber": ["paid point"]},
    "cyber": {"cve_ids": ["CVE-2026-1"], "cvss": {"score": 9.8}, "exploitation": {"kev_listed": True}},
    "finance": {"tickers": ["INFY"], "catalyst": "regulatory_action"},
    "coverage": {"single_origin": False, "origins": {"IN": 2}},
}


def _client(unlocked: set[str], user):
    """A fake DB for the anonymous or signed-in path. `unlocked` answers lens_unlocks."""
    import api.routes.events as events
    from api.main import app
    from common import auth

    eid = uuid.uuid4()

    class _R:
        def __init__(self, sql): self.sql = sql
        def mappings(self): return self
        def scalars(self): return self
        def first(self):
            if "FROM events WHERE id" in self.sql:
                return {"id": eid, "title": "t", "summary": "s", "sector": "cybersecurity",
                        "subsector": None, "image_url": None, "regions": [], "occurred_at": None,
                        "last_updated_at": T0, "projection": PROJECTION}
            return None
        def all(self):
            if "FROM lens_unlocks" in self.sql:
                return sorted(unlocked)
            return []

    class _S:
        async def execute(self, stmt, *a, **kw): return _R(str(stmt))

    async def fake_db():
        yield _S()

    async def resolve(db, token):
        return user if token == "good" else None

    return app, events, auth, fake_db, resolve, eid


async def _get(unlocked, user, headers=None, monkeypatch=None):
    app, events, auth, fake_db, resolve, eid = _client(unlocked, user)
    monkeypatch.setattr(auth, "resolve_session", resolve)
    app.dependency_overrides[events.get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get(f"/api/v1/events/{eid}", headers=headers or {})
            assert r.status_code == 200, r.text
            return r.json()
    finally:
        app.dependency_overrides.pop(events.get_db, None)


@pytest.mark.asyncio(loop_scope="session")
async def test_anonymous_gets_no_paid_prose_and_no_paid_facts(monkeypatch):
    body = await _get(set(), None, monkeypatch=monkeypatch)
    # the prose gate from f230e0d
    assert set(body["lens_briefs"]) == {"reader"}
    assert body["lens_points"] == {}
    assert set(body["projection"]["lens_briefs"]) == {"reader"}
    # the FACTS gate: the rail must have nothing to render for a locked lens
    assert body["projection"]["cyber"] is None, "KEV/CVSS left with the payload for a locked lens"
    assert body["projection"]["finance"] is None, "tickers/catalyst left with the payload for a locked lens"
    # ...but the lens still EXISTS, because the flip to a locked lens is the upgrade moment
    assert {"cyber", "markets"} <= set(body["available_lenses"])
    # and the free field on projection is untouched
    assert body["projection"]["coverage"] == {"single_origin": False, "origins": {"IN": 2}}


@pytest.mark.asyncio(loop_scope="session")
async def test_one_unlock_opens_exactly_that_lens(monkeypatch):
    uid = uuid.uuid4()
    body = await _get({"cyber"}, uid, headers={"Authorization": "Bearer good"}, monkeypatch=monkeypatch)
    assert set(body["lens_briefs"]) == {"reader", "cyber"}
    assert body["projection"]["cyber"] == PROJECTION["cyber"], "the lens they paid for lost its facts"
    assert body["projection"]["finance"] is None, "an unlock of cyber must not open markets"
    assert body["lens_points"] == {"cyber": ["paid point"]}
