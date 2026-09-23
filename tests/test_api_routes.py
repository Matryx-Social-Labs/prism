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
    ("GET", "/api/v1/sitemap/records"),
    ("GET", "/api/v1/sitemap/entities"),
    ("GET", "/api/v1/entity/{slug}"),
    ("GET", "/api/v1/subjects"),
    ("GET", "/api/v1/subject/{path}"),
    ("GET", "/api/v1/regions"),
    ("GET", "/api/v1/professions"),
    ("GET", "/api/v1/languages"),
    ("POST", "/api/v1/auth/request"),
    ("POST", "/api/v1/auth/verify"),
    ("POST", "/api/v1/auth/google"),
    ("GET", "/api/v1/billing/plans"),
    ("POST", "/api/v1/billing/razorpay/webhook"),
    ("POST", "/api/v1/billing/checkout"),
    ("POST", "/api/v1/billing/verify"),
    ("POST", "/api/v1/billing/cancel"),
    ("POST", "/api/v1/billing/pause"),
    ("POST", "/api/v1/billing/resume"),
    ("POST", "/api/v1/billing/refund"),
    ("GET", "/api/v1/billing/history"),
    ("GET", "/api/v1/billing/me"),
    ("POST", "/api/v1/auth/profile"),
    ("GET", "/api/v1/auth/me"),
    ("DELETE", "/api/v1/auth/session"),
    ("GET", "/api/v1/feed"),
    ("GET", "/api/v1/search"),
    ("GET", "/api/v1/digest/markets"),
    ("GET", "/api/v1/trending"),
    ("GET", "/api/v1/trending/{slug}"),
    ("GET", "/api/v1/events/{event_id}"),
    ("GET", "/api/v1/events/{event_id}/brief"),
    ("GET", "/api/v1/events/{event_id}/questions"),
    ("POST", "/api/v1/events/{event_id}/ask"),
    ("GET", "/api/v1/watchlist"),
    ("POST", "/api/v1/watchlist"),
    ("DELETE", "/api/v1/watchlist"),
    ("GET", "/api/v1/watchlist/events"),
    ("POST", "/api/v1/admin/pipeline/run"),
    ("GET", "/api/v1/admin/status"),
    # The /admin dashboard, guarded by a founder account (api/deps.require_admin_user).
    ("GET", "/api/v1/admin/me"),
    ("GET", "/api/v1/admin/audit"),
    # Running the labeller workspace from /admin (api/routes/admin_labellers.py).
    ("GET", "/api/v1/admin/labellers"),
    ("POST", "/api/v1/admin/labellers/status"),
    ("POST", "/api/v1/admin/labellers/add"),
    ("POST", "/api/v1/admin/labellers/qualify"),
    ("GET", "/api/v1/admin/batches"),
    ("POST", "/api/v1/admin/batches/{key}/listed"),
    ("POST", "/api/v1/admin/batches/{key}/open"),
    ("POST", "/api/v1/admin/batches/{key}/languages"),
    ("GET", "/api/v1/admin/batches/{key}/items"),
    ("PUT", "/api/v1/admin/batches/{key}/explanations"),
    # The product's numbers for founders and investors (api/routes/admin_metrics.py).
    ("GET", "/api/v1/admin/metrics"),
    ("GET", "/api/v1/admin/metrics/weekly.csv"),
    # People, read-only switches, and the collection trigger (api/routes/admin_controls.py).
    ("GET", "/api/v1/admin/people"),
    ("GET", "/api/v1/admin/flags"),
    ("POST", "/api/v1/admin/pipeline/trigger"),
    # Cookieless usage counts from the web (api/routes/beacon.py).
    ("POST", "/api/v1/beacon"),
    # Labelling — how the gold set grows without a checkout (api/routes/label.py).
    ("POST", "/api/v1/label/{key}/join"),
    ("GET", "/api/v1/label/{key}"),
    ("GET", "/api/v1/label/{key}/next"),
    ("POST", "/api/v1/label/{key}/answer"),
    ("GET", "/api/v1/label/{key}/export"),
    # The labeller workspace in front of it: apply, approval, your batches (api/routes/labeller.py).
    ("GET", "/api/v1/labeller/me"),
    ("POST", "/api/v1/labeller/apply"),
    ("GET", "/api/v1/labeller/batches"),
    ("POST", "/api/v1/labeller/batches/{key}/start"),
    # Practice and the qualification test for a task kind (phase 3).
    ("POST", "/api/v1/labeller/practice/{kind}/start"),
    ("POST", "/api/v1/labeller/qualify/{kind}/start"),
    # Guides, served only to applicants and to a batch's own invites (plan: guides behind sign-in).
    ("GET", "/api/v1/labeller/guides/{kind}"),
    ("GET", "/api/v1/label/{key}/guide"),
}


def test_route_surface_matches_expected():
    paths = app.openapi().get("paths", {})
    served = {(method.upper(), path) for path, ops in paths.items() for method in ops}
    assert served == EXPECTED, {"missing": EXPECTED - served, "extra": served - EXPECTED}


def test_healthz_exposes_a_bounded_freshness_window():
    parameters = app.openapi()["paths"]["/healthz"]["get"]["parameters"]
    window = next(p for p in parameters if p["name"] == "freshness_window_hours")

    assert window["in"] == "query"
    assert window["schema"] == {
        "type": "integer",
        "maximum": 168,
        "minimum": 1,
        "description": "Recent observation window used for stage-latency telemetry.",
        "default": 24,
        "title": "Freshness Window Hours",
    }
