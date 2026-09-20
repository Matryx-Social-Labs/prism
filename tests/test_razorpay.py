"""Razorpay: plans found-or-made by our key, the checkout signature, the routes.

Money paths, so each one has a check: a plan is matched by key AND amount (a
price change must make a new plan, never charge the old figure); the browser's
success callback is trusted only with a valid HMAC; checkout refuses politely
until the keys exist; a verified checkout turns the row active; cancel keeps
access to the period's end.
"""

import hashlib
import hmac
import json
import uuid

import httpx
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from api.main import app
from common import razorpay
from common.config import get_settings
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")

SPEC = razorpay.PlanSpec(key="plus_monthly", label="Plus · monthly", paise=14900, period="month")


SUB_STATE: dict = {"status": "created", "paid_count": 0, "current_end": None}


def _mock(plans: list[dict], calls: list[tuple[str, str, dict | None]]):
    def handler(req: httpx.Request) -> httpx.Response:
        body = json.loads(req.content) if req.content else None
        calls.append((req.method, req.url.path, body))
        if req.method == "GET" and req.url.path.startswith("/v1/subscriptions/"):
            sid = req.url.path.split("/")[-1]
            return httpx.Response(200, json={"id": sid, "notes": {"user_id": SUB_STATE.get("user_id", ""), "plan": "plus_monthly", "price_paise": "14900"}, **SUB_STATE})
        if req.method == "GET" and req.url.path == "/v1/plans":
            return httpx.Response(200, json={"items": plans})
        if req.method == "POST" and req.url.path == "/v1/plans":
            return httpx.Response(200, json={"id": "plan_new", **body})
        if req.method == "POST" and req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"id": "sub_1", "status": "created", **body})
        if req.method == "POST" and req.url.path.endswith("/cancel"):
            return httpx.Response(200, json={"id": req.url.path.split("/")[-2], "status": "cancelled", "current_end": SUB_STATE.get("current_end"), "notes": {"user_id": SUB_STATE.get("user_id", ""), "plan": "plus_monthly"}})
        return httpx.Response(404, json={"error": "unexpected"})

    return httpx.AsyncClient(base_url=razorpay.BASE, transport=httpx.MockTransport(handler))


@pytest.fixture(autouse=True)
def _fresh_cache():
    razorpay._plan_cache.clear()
    yield
    razorpay._plan_cache.clear()


async def test_a_plan_is_matched_by_key_and_amount_and_otherwise_made():
    calls: list = []
    existing = [{"id": "plan_old", "notes": {"key": "plus_monthly"}, "item": {"amount": 14900}}]
    async with _mock(existing, calls) as c:
        assert await razorpay.ensure_plan(SPEC, c) == "plan_old"
        assert [m for m, _, _ in calls] == ["GET"], "found: nothing created"
    calls.clear()
    razorpay._plan_cache.clear()
    # The same key at a NEW price is a new plan: the old figure is never charged.
    async with _mock(existing, calls) as c:
        pid = await razorpay.ensure_plan(razorpay.PlanSpec("plus_monthly", "Plus · monthly", 19900, "month"), c)
    assert pid == "plan_new"
    made = next(b for m, p, b in calls if m == "POST" and p == "/v1/plans")
    assert made["item"]["amount"] == 19900 and made["period"] == "monthly" and made["notes"] == {"key": "plus_monthly"}


async def test_a_subscription_carries_the_owner_the_plan_and_the_price_for_the_webhook():
    calls: list = []
    async with _mock([], calls) as c:
        sub = await razorpay.create_subscription(razorpay.PlanSpec("founding", "Founding", 99900, "year"), "user-1", c)
    assert sub["id"] == "sub_1"
    body = next(b for m, p, b in calls if p == "/v1/subscriptions")
    assert body["notes"] == {"user_id": "user-1", "plan": "founding", "price_paise": "99900"}
    assert body["total_count"] == razorpay.TOTAL_COUNT["founding"] == 3
    # Off the offer, the key says so but the webhook still files it under the plan.
    calls.clear()
    razorpay._plan_cache.clear()
    async with _mock([], calls) as c:
        await razorpay.create_subscription(razorpay.PlanSpec("plus_yearly_regular", "Plus · yearly", 149900, "year"), "user-1", c)
    assert next(b for m, p, b in calls if p == "/v1/subscriptions")["notes"]["plan"] == "plus_yearly"


def test_the_checkout_signature_is_razorpays_hmac_or_nothing(monkeypatch):
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret")
    good = hmac.new(b"s3cret", b"pay_1|sub_1", hashlib.sha256).hexdigest()
    assert razorpay.verify_checkout_signature("pay_1", "sub_1", good)
    assert not razorpay.verify_checkout_signature("pay_1", "sub_2", good), "a signature is for one subscription"
    assert not razorpay.verify_checkout_signature("pay_1", "sub_1", "")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "")
    assert not razorpay.verify_checkout_signature("pay_1", "sub_1", good), "no secret, no trust"


async def _db() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def _account():
    """A signed-in reader: user + session token, cleaned by the caller."""
    from common.auth import create_session, user_for_verified_email

    email = f"razorpay-{uuid.uuid4().hex[:8]}@t.test"
    async with session_scope() as s:
        uid = await user_for_verified_email(s, email)
        token = await create_session(s, uid)
    return uid, token, email


async def _cleanup(email: str):
    async with session_scope() as s:
        await s.execute(text("DELETE FROM subscriptions WHERE user_id IN (SELECT id FROM users WHERE email = :e)"), {"e": email})
        await s.execute(text("DELETE FROM sessions WHERE user_id IN (SELECT id FROM users WHERE email = :e)"), {"e": email})
        await s.execute(text("DELETE FROM usage_quota WHERE user_id IN (SELECT id FROM users WHERE email = :e)"), {"e": email})
        await s.execute(text("DELETE FROM users WHERE email = :e"), {"e": email})


async def test_checkout_refuses_until_the_keys_exist_and_plans_say_so(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "razorpay_key_id", "")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "")
    uid, token, email = await _account()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/v1/billing/plans")
            assert r.status_code == 200 and r.json()["checkout_ready"] is False
            r = await c.post("/api/v1/billing/checkout", json={"plan": "plus_monthly"}, headers={"Authorization": f"Bearer {token}"})
            assert r.status_code == 503
    finally:
        await _cleanup(email)


async def test_checkout_then_verify_turns_plus_on_and_cancel_keeps_it_to_period_end(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "razorpay_key_id", "rzp_test_x")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret")
    calls: list = []
    monkeypatch.setattr(razorpay, "_client", lambda: _mock([], calls))
    sent: list = []

    async def _no_mail(db, user_id, before, after, sub):
        sent.append((before, after))

    monkeypatch.setattr(razorpay, "on_transition", _no_mail)
    uid, token, email = await _account()
    auth = {"Authorization": f"Bearer {token}"}
    SUB_STATE.clear()
    SUB_STATE.update({"status": "created", "paid_count": 0, "current_end": None, "user_id": str(uid)})
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/api/v1/billing/checkout", json={"plan": "plus_monthly"}, headers=auth)
            assert r.status_code == 200, r.text
            out = r.json()
            assert out["subscription_id"] == "sub_1" and out["key_id"] == "rzp_test_x" and out["amount_paise"] == 14900
            # Not yet paid: still free.
            r = await c.get("/api/v1/auth/me", headers=auth)
            assert r.json()["plan"] == "free"
            # A forged callback is refused …
            r = await c.post("/api/v1/billing/verify", json={"razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_1", "razorpay_signature": "nope"}, headers=auth)
            assert r.status_code == 400
            # … the real one turns Plus on at once, with Razorpay's own dates —
            # and a one-charge subscription that Razorpay calls 'completed' is
            # still PAID UP to current_end, so it is active, not expired.
            SUB_STATE.update({"status": "completed", "paid_count": 1, "current_end": 4102444800})
            sig = hmac.new(b"s3cret", b"pay_1|sub_1", hashlib.sha256).hexdigest()
            r = await c.post("/api/v1/billing/verify", json={"razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_1", "razorpay_signature": sig}, headers=auth)
            assert r.status_code == 200 and r.json()["plan"] == "plus_monthly" and r.json()["entitled"] is True
            r = await c.get("/api/v1/auth/me", headers=auth)
            assert r.json()["plan"] == "plus"
            r = await c.get("/api/v1/billing/me", headers=auth)
            assert r.json()["current_period_end"].startswith("2100-01-01")
            assert sent == [("created", "active")], "the welcome email is owed exactly once"
            # A second checkout while subscribed is refused.
            r = await c.post("/api/v1/billing/checkout", json={"plan": "plus_yearly"}, headers=auth)
            assert r.status_code == 409
            # Cancel: the provider is told to stop at cycle end; access continues.
            r = await c.post("/api/v1/billing/cancel", headers=auth)
            assert r.status_code == 200
            assert any(p.endswith("/sub_1/cancel") and b == {"cancel_at_cycle_end": 1} for _, p, b in calls)
            r = await c.get("/api/v1/billing/me", headers=auth)
            assert r.json()["status"] == "active" and r.json()["cancel_at"] is not None
            r = await c.get("/api/v1/auth/me", headers=auth)
            assert r.json()["plan"] == "plus", "cancelling never cuts the paid period short"
    finally:
        await _cleanup(email)


async def test_reconcile_finds_a_paid_checkout_the_webhook_missed(monkeypatch):
    """The first real test purchase: Checkout said success, our page never heard
    (an earlier payment.failed had ended the flow), no webhook landed, and the
    row sat at 'created'. The hourly reconcile asks Razorpay and fixes it."""
    if not await _db():
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "razorpay_key_id", "rzp_test_x")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret")
    calls: list = []
    monkeypatch.setattr(razorpay, "_client", lambda: _mock([], calls))
    sent: list = []

    async def _no_mail(db, user_id, before, after, sub):
        sent.append((before, after))

    monkeypatch.setattr(razorpay, "on_transition", _no_mail)
    uid, token, email = await _account()
    SUB_STATE.clear()
    SUB_STATE.update({"status": "active", "paid_count": 1, "current_end": 4102444800, "user_id": str(uid)})
    try:
        async with session_scope() as s:
            await s.execute(text("INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, price_paise, notes, created_at) VALUES (gen_random_uuid(), :u, 'razorpay', 'sub_missed', 'plus_monthly', 'created', 14900, 'checkout opened', now() - interval '10 minutes')"), {"u": str(uid)})
        async with session_scope() as s:
            changed = await razorpay.reconcile_pending(s)
        assert changed == 1 and sent == [("created", "active")]
        async with session_scope() as s:
            row = (await s.execute(text("SELECT status, current_period_end FROM subscriptions WHERE provider_sub_id = 'sub_missed'"))).first()
        assert row[0] == "active" and row[1] is not None
    finally:
        await _cleanup(email)


def test_the_status_map_keeps_a_paid_up_completed_subscription_active():
    assert razorpay.STATUS["completed"] == "active"
    assert razorpay.STATUS["authenticated"] == "active"
    assert razorpay.STATUS["pending"] == "past_due"
    assert razorpay.STATUS["expired"] == "expired"
    assert razorpay.TOTAL_COUNT["plus_yearly"] > 1, "a one-charge subscription completes on payment and never reads as active"
