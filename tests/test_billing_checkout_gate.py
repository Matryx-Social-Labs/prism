"""Checkout stays shut on Razorpay test keys (founder, 2026-09-29: "hide
checkout as of now"). A test key's sheet takes no money, so a reader who met it
would "pay" and get nothing; the plans say `checkout_ready: false` and the one
route that makes a subscription answers 503, unless PRISM_ALLOW_TEST_CHECKOUT.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from api.routes.billing import CHECKOUT_CLOSED, checkout_open
from common.config import get_settings
from tests.test_razorpay import _account, _cleanup, _db


def _keys(monkeypatch, key_id: str, allow: bool = False):
    monkeypatch.setattr(get_settings(), "razorpay_key_id", key_id)
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret" if key_id else "")
    monkeypatch.setattr(get_settings(), "prism_allow_test_checkout", allow)


@pytest.mark.parametrize(
    ("key_id", "allow", "open_"),
    [
        ("", False, False),
        ("", True, False),
        ("rzp_test_abc", False, False),
        ("rzp_test_abc", True, True),
        ("rzp_live_abc", False, True),
    ],
)
def test_checkout_opens_only_on_live_keys_or_when_test_checkout_is_allowed(monkeypatch, key_id, allow, open_):
    _keys(monkeypatch, key_id, allow)
    assert checkout_open() is open_


@pytest.mark.asyncio(loop_scope="session")
async def test_test_keys_hide_checkout_in_the_plans_and_refuse_it_at_the_route(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    _keys(monkeypatch, "rzp_test_abc")
    uid, token, email = await _account()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/v1/billing/plans")
            assert r.status_code == 200 and r.json()["checkout_ready"] is False
            r = await c.post("/api/v1/billing/checkout", json={"plan": "plus_monthly"}, headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 503 and r.json()["detail"] == CHECKOUT_CLOSED
            _keys(monkeypatch, "rzp_live_abc")
            r = await c.get("/api/v1/billing/plans")
            assert r.json()["checkout_ready"] is True
    finally:
        await _cleanup(email)
