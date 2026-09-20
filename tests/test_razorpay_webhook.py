"""The webhook must never 500: Razorpay retries a failing endpoint and then stops delivering."""

import hashlib
import hmac
import json

import pytest
from httpx import ASGITransport, AsyncClient

from api.main import app
from common import razorpay
from common.config import get_settings

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_a_signed_subscription_event_is_applied_and_answered_200(monkeypatch):
    monkeypatch.setattr(get_settings(), "razorpay_webhook_secret", "whsec")
    applied: list = []

    async def _apply(db, sub, *, note):
        applied.append((sub["id"], note))
        return "user-1", "created", "active"

    async def _mail(*a):
        return None

    monkeypatch.setattr(razorpay, "apply_subscription", _apply)
    monkeypatch.setattr(razorpay, "on_transition", _mail)
    payload = json.dumps({"event": "subscription.activated", "payload": {"subscription": {"entity": {"id": "sub_9", "status": "active", "notes": {"user_id": "user-1", "plan": "plus_monthly"}}}}}).encode()
    sig = hmac.new(b"whsec", payload, hashlib.sha256).hexdigest()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v1/billing/razorpay/webhook", content=payload, headers={"x-razorpay-signature": sig, "content-type": "application/json"})
    # REGRESSION: a kwarg named `event` on the structlog call raised a TypeError here
    # and every delivery 500'd (2026-09-20).
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "active" and applied == [("sub_9", "subscription.activated")]
