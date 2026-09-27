"""Browser cache headers on the public API reads (api/cache_headers.py).

Audit, 2026-09-27: 15 of 17 public GETs sent no Cache-Control, so a reader's
browser asked Singapore again for the same feed, digest or taxonomy on every
visit. The risk in fixing that is marking public something that depends on who
is asking — a paid lens served from one reader's cache to the next. So the
list is explicit, and the guard here reads every listed route's signature.
"""

import importlib
import pkgutil

import pytest
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient

import api.routes
from api import deps
from api.cache_headers import PublicCacheHeaders, cache_control_for
from api.main import app

pytestmark = pytest.mark.asyncio(loop_scope="session")

_IDENTITY = {deps.get_current_user, deps.get_current_user_optional, deps.require_admin_user, deps.require_admin}


def _get_routes() -> list[APIRoute]:
    routes = []
    for m in pkgutil.iter_modules(api.routes.__path__):
        router = getattr(importlib.import_module(f"api.routes.{m.name}"), "router", None)
        routes += [r for r in getattr(router, "routes", []) if isinstance(r, APIRoute) and "GET" in r.methods]
    return routes


def _calls(dependant) -> set:
    out = set()
    for sub in dependant.dependencies:
        out |= {sub.call} | _calls(sub)
    return out


def _example(path: str) -> str:
    """A concrete URL for a route template: /api/v1/entity/{slug} → /api/v1/entity/x."""
    import re

    return re.sub(r"\{[^}]+\}", "x", path)


def test_no_route_that_knows_the_reader_is_ever_marked_public():
    listed = [r for r in _get_routes() if cache_control_for(_example(r.path))]
    assert len(listed) >= 12, "the allowlist matched fewer routes than it names — a pattern went stale"
    for r in listed:
        assert not (_calls(r.dependant) & _IDENTITY), f"{r.path} reads the session but is cached as public"
        assert r.dependant.request_param_name is None, f"{r.path} takes the raw Request (cookies) but is cached as public"


@pytest.mark.parametrize("path", [
    "/api/v1/events/x", "/api/v1/events/x/brief", "/api/v1/events/x/questions",
    "/api/v1/watchlist", "/api/v1/watchlist/events", "/api/v1/auth/me", "/api/v1/billing/me",
    "/api/v1/admin/spend", "/api/v1/label/x",
])
def test_reader_specific_reads_stay_uncached(path):
    assert cache_control_for(path) is None


async def test_public_reads_tell_the_browser_how_long_to_keep_them():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/taxonomy")
    assert r.status_code == 200
    assert r.headers["cache-control"] == "public, max-age=3600, stale-while-revalidate=7200"


async def _serve(status: int, headers: list[tuple[bytes, bytes]], method: str = "GET"):
    async def inner(scope, receive, send):
        await send({"type": "http.response.start", "status": status, "headers": headers})
        await send({"type": "http.response.body", "body": b"{}"})

    sent = []

    async def send(message):
        sent.append(message)

    scope = {"type": "http", "method": method, "path": "/api/v1/feed", "headers": []}
    await PublicCacheHeaders(inner)(scope, None, send)
    return dict(sent[0]["headers"])


async def test_only_a_successful_get_is_marked():
    assert (await _serve(200, []))[b"cache-control"] == b"public, max-age=30, stale-while-revalidate=60"
    assert b"cache-control" not in await _serve(404, []), "an error must not be cached"
    assert b"cache-control" not in await _serve(200, [], method="POST")


async def test_a_routes_own_policy_wins():
    """subject.py sets s-maxage for itself; the middleware never overwrites."""
    assert (await _serve(200, [(b"cache-control", b"no-store")]))[b"cache-control"] == b"no-store"
