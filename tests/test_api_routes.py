"""Route-surface guard: the app must expose exactly these endpoints.

Locks the router split (api/routes/*) against accidental drift — a moved or
dropped route fails here instead of in production. Update EXPECTED deliberately
when adding endpoints (auth/billing/watchlist land here in later freemium PRs).
"""

from api.main import app

EXPECTED = {
    ("GET", "/healthz"),
    ("GET", "/api/v1/lenses"),
    ("GET", "/api/v1/taxonomy"),
    ("POST", "/api/v1/auth/request"),
    ("POST", "/api/v1/auth/verify"),
    ("GET", "/api/v1/auth/me"),
    ("GET", "/api/v1/feed"),
    ("GET", "/api/v1/events/{event_id}"),
    ("GET", "/api/v1/events/{event_id}/brief"),
    ("GET", "/api/v1/events/{event_id}/questions"),
    ("POST", "/api/v1/events/{event_id}/ask"),
    ("GET", "/api/v1/watchlist"),
    ("POST", "/api/v1/watchlist"),
    ("DELETE", "/api/v1/watchlist"),
    ("GET", "/api/v1/watchlist/events"),
    ("POST", "/api/v1/admin/pipeline/run"),
}


def test_route_surface_matches_expected():
    paths = app.openapi().get("paths", {})
    served = {(method.upper(), path) for path, ops in paths.items() for method in ops}
    assert served == EXPECTED, {"missing": EXPECTED - served, "extra": served - EXPECTED}
