"""Ask usage must be attributable, without shutting anonymous readers out.

`AgentSession.user_ref` was the literal string 'default' for every session ever
created, so nothing could tell one person's questions from another's. That makes
per-user metering impossible, and metering is a stated prerequisite for charging
for Ask — the Markets tier prices unlimited questions.

The opposite failure matters just as much: Ask is deliberately open to anonymous
readers. A login wall on it would cost the free funnel the product is built to
gather, so identity is OPTIONAL and a missing or lapsed token must degrade to
anonymous rather than 401.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from api.deps import get_current_user_optional

pytestmark = pytest.mark.asyncio


class _FakeDB:
    pass


def _req(cookie: str | None = None, method: str = "GET", origin: str | None = None):
    from starlette.requests import Request

    headers = []
    if cookie:
        headers.append((b"cookie", f"prism_session={cookie}".encode()))
    if origin:
        headers.append((b"origin", origin.encode()))
    return Request({"type": "http", "method": method, "headers": headers, "path": "/", "query_string": b""})


async def test_no_token_is_anonymous_not_an_error(monkeypatch):
    assert await get_current_user_optional(request=_req(), authorization="", db=_FakeDB()) is None


async def test_a_lapsed_token_is_anonymous_not_an_error(monkeypatch):
    """Someone whose session expired mid-read should get an answer, not an error
    they cannot act on."""
    from common import auth

    async def expired(db, token):
        return None

    monkeypatch.setattr(auth, "resolve_session", expired)
    got = await get_current_user_optional(request=_req(), authorization="Bearer stale", db=_FakeDB())
    assert got is None


async def test_a_valid_token_is_resolved_so_usage_can_be_attributed(monkeypatch):
    from common import auth

    uid = uuid.uuid4()

    async def resolve(db, token):
        assert token == "good"
        return uid

    monkeypatch.setattr(auth, "resolve_session", resolve)
    assert await get_current_user_optional(request=_req(), authorization="Bearer good", db=_FakeDB()) == uid


async def test_a_non_bearer_scheme_is_anonymous(monkeypatch):
    """Basic auth, or a raw token pasted without the scheme, must not be treated
    as a session id."""
    from common import auth

    async def boom(db, token):  # must never be reached
        raise AssertionError("resolve_session called for a non-bearer scheme")

    monkeypatch.setattr(auth, "resolve_session", boom)
    assert await get_current_user_optional(request=_req(), authorization="Basic abc", db=_FakeDB()) is None


async def test_the_session_records_the_user_rather_than_a_placeholder(monkeypatch):
    """The regression: every session was written with user_ref='default'."""
    import agent.rag as rag

    captured = {}

    class _S:
        def add(self, obj):
            captured["user_ref"] = obj.user_ref
            obj.id = uuid.uuid4()

        async def flush(self):
            return None

        async def get(self, *a, **kw):
            return None

    class _Scope:
        async def __aenter__(self):
            return _S()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(rag, "session_scope", lambda: _Scope())
    uid = str(uuid.uuid4())
    await rag.ensure_session(uuid.uuid4(), None, user_ref=uid)
    assert captured["user_ref"] == uid

    await rag.ensure_session(uuid.uuid4(), None, user_ref=None)
    assert captured["user_ref"] is None, "anonymous must be NULL, distinguishable from 'default'"


async def test_the_ASK_ROUTE_actually_passes_the_user_through(monkeypatch):
    """The wiring, not the parts.

    Every assertion above passed with the route hardcoding `user_ref=None` — the
    helpers were correct and nothing connected them. That is the third time today
    a unit test covered a function while the call site was broken, so this drives
    the real endpoint.
    """
    import agent.rag as rag
    import api.routes.events as events
    from api.main import app
    from common import auth

    uid = uuid.uuid4()
    seen = {}

    async def fake_ensure(event_id, session_id, user_ref=None):
        seen["user_ref"] = user_ref
        return uuid.uuid4()

    async def fake_stream(**kw):
        if False:
            yield {}

    async def resolve(db, token):
        return uid if token == "good" else None

    monkeypatch.setattr(events, "ensure_session", fake_ensure)
    monkeypatch.setattr(events, "answer_stream", fake_stream)
    monkeypatch.setattr(auth, "resolve_session", resolve)
    monkeypatch.setattr(rag, "ensure_session", fake_ensure)

    # The event lookup is the only database touch left on this path.
    async def fake_db():
        class _R:
            def scalar_one_or_none(self):
                return 1

            def scalar_one(self):
                # The Ask allowance counts prior questions; 0 keeps this test
                # about ATTRIBUTION rather than about the quota.
                return 0

            def all(self):
                # The plan lookup (common/billing.plan_for): no subscription rows → free.
                return []

        class _S:
            async def execute(self, *a, **kw):
                return _R()

        yield _S()

    app.dependency_overrides[events.get_db] = fake_db
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post(f"/api/v1/events/{uuid.uuid4()}/ask",
                             json={"question": "who said it?"},
                             headers={"Authorization": "Bearer good"})
            assert r.status_code == 200
            assert seen["user_ref"] == str(uid), (
                "the signed-in user did not reach the session row; Ask usage is "
                "unattributable and cannot be metered"
            )

            seen.clear()
            r = await c.post(f"/api/v1/events/{uuid.uuid4()}/ask",
                             json={"question": "who said it?"})
            assert r.status_code == 200, "anonymous Ask must keep working"
            assert seen["user_ref"] is None
    finally:
        app.dependency_overrides.pop(events.get_db, None)
