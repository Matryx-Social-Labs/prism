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
from datetime import UTC, datetime

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
            state = SUB_STATE.get("subs", {}).get(sid, SUB_STATE)
            notes = {"user_id": SUB_STATE.get("user_id", ""), "plan": state.get("plan", "plus_monthly"), "price_paise": state.get("price_paise", "14900"), **state.get("notes", {})}
            return httpx.Response(200, json={"id": sid, **{k: v for k, v in state.items() if k not in ("subs", "invoices")}, "notes": notes})
        if req.method == "GET" and req.url.path == "/v1/plans":
            return httpx.Response(200, json={"items": plans})
        if req.method == "POST" and req.url.path == "/v1/plans":
            return httpx.Response(200, json={"id": "plan_new", **body})
        if req.method == "POST" and req.url.path == "/v1/subscriptions":
            return httpx.Response(200, json={"id": SUB_STATE.get("next_id", "sub_1"), "status": "created", **body})
        if req.method == "POST" and req.url.path.endswith("/pause"):
            if SUB_STATE.get("pause_unavailable"):
                return httpx.Response(400, json={"error": {"code": "BAD_REQUEST_ERROR", "description": "Pause is not enabled for this account."}})
            SUB_STATE["status"] = "paused"
            return httpx.Response(200, json={"id": req.url.path.split("/")[-2], **{k: v for k, v in SUB_STATE.items() if k not in ("subs", "invoices")}, "notes": {"user_id": SUB_STATE.get("user_id", ""), "plan": SUB_STATE.get("plan", "plus_monthly")}})
        if req.method == "POST" and req.url.path.endswith("/resume"):
            SUB_STATE["status"] = "active"
            return httpx.Response(200, json={"id": req.url.path.split("/")[-2], **{k: v for k, v in SUB_STATE.items() if k not in ("subs", "invoices")}, "notes": {"user_id": SUB_STATE.get("user_id", ""), "plan": SUB_STATE.get("plan", "plus_monthly")}})
        if req.method == "GET" and req.url.path == "/v1/invoices":
            inv = SUB_STATE.get("invoices", [])
            return httpx.Response(200, json={"count": len(inv), "items": inv})
        if req.method == "POST" and req.url.path.startswith("/v1/payments/") and req.url.path.endswith("/refund"):
            return httpx.Response(200, json={"id": "rfnd_1", "payment_id": req.url.path.split("/")[-2], "amount": body["amount"], "speed_processed": body.get("speed"), "status": "pending"})
        if req.method == "POST" and req.url.path.endswith("/cancel"):
            if SUB_STATE.get("status") == "completed":
                return httpx.Response(400, json={"error": {"code": "BAD_REQUEST_ERROR", "description": "Subscription is not cancellable in completed status.", "field": "status"}})
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
            # A completed (paid-up, one-charge) subscription already records its end.
            r = await c.get("/api/v1/billing/me", headers=auth)
            assert r.json()["status"] == "active" and r.json()["cancel_at"] is not None
            # Cancel on it: Razorpay says there is nothing to cancel; that is not an error for the reader.
            r = await c.post("/api/v1/billing/cancel", headers=auth)
            assert r.status_code == 200, r.text
            assert r.json()["access_until"].startswith("2100-01-01")
            # A renewing subscription: the provider is told to stop at cycle end; access continues.
            SUB_STATE.update({"status": "active", "remaining_count": 9})
            async with session_scope() as s:
                await s.execute(text("UPDATE subscriptions SET cancel_at = NULL WHERE provider_sub_id = 'sub_1'"))
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


def test_the_refund_window_is_seven_days_on_yearly_and_founding_and_nothing_else():
    from datetime import UTC, datetime, timedelta

    start = datetime(2026, 9, 21, tzinfo=UTC)
    assert razorpay.refundable_until("plus_yearly", "active", start, None) == start + timedelta(days=7)
    assert razorpay.refundable_until("founding", "active", start, None) == start + timedelta(days=7)
    assert razorpay.refundable_until("plus_monthly", "active", start, None) is None, "monthly is never refunded"
    assert razorpay.refundable_until("plus_yearly", "past_due", start, None) is None
    assert razorpay.refundable_until("plus_yearly", "active", None, None) is None, "no start known: nothing offered"
    assert razorpay.refundable_until("plus_yearly", "active", start, "rfnd_1") is None, "offered once"


async def test_refund_inside_the_window_goes_back_in_full_and_ends_plus_at_once(monkeypatch):
    """The Refund policy as one click: the latest paid invoice's payment is
    refunded for what was paid, the row records the refund BEFORE the cancel is
    asked (so a racing webhook sends nothing on top), the subscription is
    cancelled now rather than at cycle end, and the reader is free again.
    Outside the window, or twice, the route refuses."""
    import time
    from datetime import UTC, datetime, timedelta

    from api.routes import billing as billing_routes

    if not await _db():
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "razorpay_key_id", "rzp_test_x")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret")
    calls: list = []
    monkeypatch.setattr(razorpay, "_client", lambda: _mock([], calls))
    mails: list = []

    async def _no_mail(db, user_id, before, after, sub):
        mails.append(("transition", before, after))

    async def _refund_mail(db, user_id, **kw):
        mails.append(("refund", kw["amount_paise"], kw["refund_id"]))

    monkeypatch.setattr(razorpay, "on_transition", _no_mail)
    monkeypatch.setattr(billing_routes, "notify_refund", _refund_mail)
    uid, token, email = await _account()
    auth = {"Authorization": f"Bearer {token}"}
    now = int(time.time())
    SUB_STATE.clear()
    SUB_STATE.update({
        "status": "created", "paid_count": 0, "current_end": None, "user_id": str(uid), "plan": "plus_yearly", "price_paise": "149900",
        "invoices": [{"id": "inv_1", "status": "paid", "payment_id": "pay_9", "amount": 149900, "amount_paid": 149900, "paid_at": now - 86400}],
    })
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.post("/api/v1/billing/checkout", json={"plan": "plus_yearly"}, headers=auth)
            assert r.status_code == 200, r.text
            SUB_STATE.update({"status": "active", "paid_count": 1, "current_start": now - 86400, "current_end": now + 364 * 86400, "remaining_count": 9})
            sig = hmac.new(b"s3cret", b"pay_9|sub_1", hashlib.sha256).hexdigest()
            r = await c.post("/api/v1/billing/verify", json={"razorpay_payment_id": "pay_9", "razorpay_subscription_id": "sub_1", "razorpay_signature": sig}, headers=auth)
            assert r.status_code == 200, r.text
            me = (await c.get("/api/v1/billing/me", headers=auth)).json()
            assert me["refundable_until"] is not None and me["refund_id"] is None
            until = datetime.fromisoformat(me["refundable_until"])
            assert timedelta(days=5) < until - datetime.now(UTC) < timedelta(days=7)
            # The click.
            r = await c.post("/api/v1/billing/refund", headers=auth)
            assert r.status_code == 200, r.text
            assert r.json()["refund_id"] == "rfnd_1" and r.json()["amount_paise"] == 149900
            refund = next((p, b) for m, p, b in calls if m == "POST" and p.endswith("/refund"))
            assert refund == ("/v1/payments/pay_9/refund", {"amount": 149900, "speed": "normal", "notes": {"user_id": str(uid), "reason": "7-day refund policy", "subscription_id": "sub_1"}})
            assert any(p.endswith("/sub_1/cancel") and b == {"cancel_at_cycle_end": 0} for _, p, b in calls), "ended now, not at cycle end"
            assert calls.index(next(x for x in calls if x[1].endswith("/refund"))) < calls.index(next(x for x in calls if x[1].endswith("/cancel"))), "refund before cancel"
            assert ("refund", 149900, "rfnd_1") in mails
            assert (await c.get("/api/v1/auth/me", headers=auth)).json()["plan"] == "free"
            me = (await c.get("/api/v1/billing/me", headers=auth)).json()
            assert me["status"] == "cancelled" and me["refund_id"] == "rfnd_1" and me["refundable_until"] is None
            # Twice: refused.
            assert (await c.post("/api/v1/billing/refund", headers=auth)).status_code == 409
            # The webhook that follows the cancel changes nothing and owes no second email.
            async with session_scope() as s:
                await razorpay.apply_subscription(s, {**SUB_STATE, "id": "sub_1", "status": "cancelled", "notes": {"user_id": str(uid), "plan": "plus_yearly"}}, note="subscription.cancelled")
                row = (await s.execute(text("SELECT refund_id, status FROM subscriptions WHERE provider_sub_id = 'sub_1'"))).one()
            assert row == ("rfnd_1", "cancelled")
    finally:
        await _cleanup(email)


async def test_refund_is_refused_once_the_window_has_closed(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "razorpay_key_id", "rzp_test_x")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret")
    calls: list = []
    monkeypatch.setattr(razorpay, "_client", lambda: _mock([], calls))
    uid, token, email = await _account()
    auth = {"Authorization": f"Bearer {token}"}
    try:
        async with session_scope() as s:
            await s.execute(
                text(
                    "INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, current_period_start, current_period_end, price_paise) "
                    "VALUES (gen_random_uuid(), :u, 'razorpay', 'sub_old', 'plus_yearly', 'active', now() - interval '8 days', now() + interval '357 days', 149900)"
                ),
                {"u": str(uid)},
            )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            me = (await c.get("/api/v1/billing/me", headers=auth)).json()
            assert me["refundable_until"] is not None and datetime_past(me["refundable_until"])
            assert (await c.post("/api/v1/billing/refund", headers=auth)).status_code == 409
            assert not any(p.endswith("/refund") for _, p, _ in calls), "Razorpay is never asked outside the window"
    finally:
        await _cleanup(email)


def datetime_past(iso: str) -> bool:
    from datetime import UTC, datetime

    return datetime.fromisoformat(iso) < datetime.now(UTC)


async def test_pause_keeps_the_paid_month_stops_charges_and_comes_back_on_its_own(monkeypatch):
    """The cancel sheet's first offer. Razorpay is paused at once; the reader
    stays Plus to the end of the paid month (entitlement is by date); the row
    remembers when to resume; the worker resumes it on that day, and a reader
    can resume sooner by hand. Cancel and pause are refused on the wrong states."""
    import time

    from api.routes import billing as billing_routes

    if not await _db():
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "razorpay_key_id", "rzp_test_x")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret")
    calls: list = []
    monkeypatch.setattr(razorpay, "_client", lambda: _mock([], calls))
    mails: list = []

    async def _transition(db, user_id, before, after, sub):
        mails.append((before, after))

    async def _paused(db, user_id, **kw):
        mails.append(("paused", kw["resumes"]))

    monkeypatch.setattr(razorpay, "on_transition", _transition)
    monkeypatch.setattr(billing_routes, "notify_paused", _paused)
    uid, token, email = await _account()
    auth = {"Authorization": f"Bearer {token}"}
    now = int(time.time())
    end = now + 20 * 86400
    SUB_STATE.clear()
    SUB_STATE.update({"status": "created", "paid_count": 0, "current_end": None, "user_id": str(uid)})
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.post("/api/v1/billing/checkout", json={"plan": "plus_monthly"}, headers=auth)).status_code == 200
            SUB_STATE.update({"status": "active", "paid_count": 1, "current_start": now - 10 * 86400, "current_end": end, "remaining_count": 11})
            sig = hmac.new(b"s3cret", b"pay_1|sub_1", hashlib.sha256).hexdigest()
            assert (await c.post("/api/v1/billing/verify", json={"razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_1", "razorpay_signature": sig}, headers=auth)).status_code == 200
            assert (await c.post("/api/v1/billing/pause", json={"months": 5}, headers=auth)).status_code == 422
            r = await c.post("/api/v1/billing/pause", json={"months": 2}, headers=auth)
            assert r.status_code == 200, r.text
            assert any(p.endswith("/sub_1/pause") and b == {"pause_at": "now"} for _, p, b in calls)
            paused_until = datetime.fromisoformat(r.json()["paused_until"])
            assert abs((paused_until - datetime.fromtimestamp(end, tz=UTC)).days - 60) <= 1, "the pause starts when the paid month ends"
            assert ("paused", paused_until) in mails
            me = (await c.get("/api/v1/billing/me", headers=auth)).json()
            assert me["status"] == "paused" and me["paused_until"] == r.json()["paused_until"]
            assert (await c.get("/api/v1/auth/me", headers=auth)).json()["plan"] == "plus", "paid time is kept"
            assert (await c.post("/api/v1/billing/pause", json={"months": 1}, headers=auth)).status_code == 409, "nothing to pause twice"
            # The worker, before the day: nothing. On the day: resumed, and the row is active again.
            async with session_scope() as s:
                assert await razorpay.resume_due(s) == 0
                await s.execute(text("UPDATE subscriptions SET paused_until = now() - interval '1 hour' WHERE provider_sub_id = 'sub_1'"))
            async with session_scope() as s:
                assert await razorpay.resume_due(s) == 1
            assert any(p.endswith("/sub_1/resume") and b == {"resume_at": "now"} for _, p, b in calls)
            me = (await c.get("/api/v1/billing/me", headers=auth)).json()
            assert me["status"] == "active" and me["paused_until"] is None
            assert ("paused", "active") in mails, "the back-on email is owed"
            # Resume by hand from a fresh pause.
            assert (await c.post("/api/v1/billing/pause", json={"months": 1}, headers=auth)).status_code == 200
            assert (await c.post("/api/v1/billing/resume", headers=auth)).status_code == 200
            assert (await c.get("/api/v1/billing/me", headers=auth)).json()["status"] == "active"
            # Razorpay without the feature: a plain 409, never a 500.
            SUB_STATE["pause_unavailable"] = True
            r = await c.post("/api/v1/billing/pause", json={"months": 1}, headers=auth)
            assert r.status_code == 409 and "not available" in r.json()["detail"]
    finally:
        await _cleanup(email)


async def test_the_yearly_from_the_cancel_sheet_starts_when_the_month_ends_and_stops_the_monthly(monkeypatch):
    """Nothing is charged twice for the same days: the yearly is created with
    start_at = the monthly's period end, and once authorised the monthly is
    told to stop at cycle end. The plan row reads: ends <date> · then yearly."""
    import time

    if not await _db():
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "razorpay_key_id", "rzp_test_x")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret")
    calls: list = []
    monkeypatch.setattr(razorpay, "_client", lambda: _mock([], calls))
    mails: list = []

    async def _transition(db, user_id, before, after, sub):
        mails.append((before, after, sub.get("id")))

    monkeypatch.setattr(razorpay, "on_transition", _transition)
    uid, token, email = await _account()
    auth = {"Authorization": f"Bearer {token}"}
    now = int(time.time())
    end = now + 12 * 86400
    SUB_STATE.clear()
    SUB_STATE.update({"status": "created", "paid_count": 0, "current_end": None, "user_id": str(uid)})
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            assert (await c.post("/api/v1/billing/checkout", json={"plan": "plus_monthly"}, headers=auth)).status_code == 200
            SUB_STATE.update({"status": "active", "paid_count": 1, "current_start": now - 18 * 86400, "current_end": end, "remaining_count": 11})
            sig = hmac.new(b"s3cret", b"pay_1|sub_1", hashlib.sha256).hexdigest()
            assert (await c.post("/api/v1/billing/verify", json={"razorpay_payment_id": "pay_1", "razorpay_subscription_id": "sub_1", "razorpay_signature": sig}, headers=auth)).status_code == 200
            # A plain second checkout is still refused …
            assert (await c.post("/api/v1/billing/checkout", json={"plan": "plus_yearly"}, headers=auth)).status_code == 409
            # … the scheduled one is made for the day the month ends.
            SUB_STATE["next_id"] = "sub_2"
            r = await c.post("/api/v1/billing/checkout", json={"plan": "plus_yearly", "start_after_current": True}, headers=auth)
            assert r.status_code == 200, r.text
            made = next(b for m, p, b in calls if m == "POST" and p == "/v1/subscriptions" and b.get("start_at"))
            assert made["start_at"] == end and made["notes"]["replaces"] == "sub_1"
            assert r.json()["starts_at"].startswith(datetime.fromtimestamp(end, tz=UTC).date().isoformat())
            # Razorpay: authorised, not started.
            SUB_STATE["subs"] = {"sub_2": {"status": "authenticated", "start_at": end, "charge_at": end, "end_at": end + 10 * 365 * 86400, "plan": "plus_yearly", "price_paise": "149900", "notes": {"replaces": "sub_1"}}}
            sig2 = hmac.new(b"s3cret", b"pay_2|sub_2", hashlib.sha256).hexdigest()
            r = await c.post("/api/v1/billing/verify", json={"razorpay_payment_id": "pay_2", "razorpay_subscription_id": "sub_2", "razorpay_signature": sig2}, headers=auth)
            assert r.status_code == 200, r.text
            assert any(p.endswith("/sub_1/cancel") and b == {"cancel_at_cycle_end": 1} for _, p, b in calls), "the monthly stops at cycle end"
            me = (await c.get("/api/v1/billing/me", headers=auth)).json()
            assert me["plan"] == "plus_monthly" and me["status"] == "active" and me["cancel_at"] is not None, "the monthly still speaks for the reader"
            assert me["next"] == {"plan": "plus_yearly", "starts_at": datetime.fromtimestamp(end, tz=UTC).isoformat(), "price_paise": 149900}
            assert ("created", "active", "sub_2") in mails
            assert (await c.get("/api/v1/auth/me", headers=auth)).json()["plan"] == "plus"
            assert (await c.post("/api/v1/billing/checkout", json={"plan": "plus_yearly", "start_after_current": True}, headers=auth)).status_code == 409, "one scheduled plan at a time"
    finally:
        await _cleanup(email)


async def test_history_lists_every_paid_invoice_with_razorpays_link_and_marks_the_refunded_one(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    monkeypatch.setattr(get_settings(), "razorpay_key_id", "rzp_test_x")
    monkeypatch.setattr(get_settings(), "razorpay_key_secret", "s3cret")
    calls: list = []
    monkeypatch.setattr(razorpay, "_client", lambda: _mock([], calls))
    uid, token, email = await _account()
    auth = {"Authorization": f"Bearer {token}"}
    SUB_STATE.clear()
    SUB_STATE.update({
        "invoices": [
            {"id": "inv_old", "status": "paid", "payment_id": "pay_a", "amount": 14900, "amount_paid": 14900, "paid_at": 1_700_000_000, "short_url": "https://rzp.io/i/old"},
            {"id": "inv_new", "status": "paid", "payment_id": "pay_b", "amount": 149900, "amount_paid": 149900, "paid_at": 1_760_000_000, "short_url": "https://rzp.io/i/new"},
            {"id": "inv_draft", "status": "issued", "payment_id": None, "amount": 149900, "issued_at": 1_770_000_000},
        ]
    })
    try:
        async with session_scope() as s:
            await s.execute(
                text(
                    "INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, price_paise, refund_id) "
                    "VALUES (gen_random_uuid(), :u, 'razorpay', 'sub_h', 'plus_yearly', 'cancelled', 149900, 'rfnd_9')"
                ),
                {"u": str(uid)},
            )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            r = await c.get("/api/v1/billing/history", headers=auth)
            assert r.status_code == 200, r.text
            rows = r.json()["payments"]
            assert [x["invoice_id"] for x in rows] == ["inv_new", "inv_old"], "paid only, newest first"
            assert rows[0] == {"paid_at": "2025-10-09T08:53:20+00:00", "plan": "plus_yearly", "amount_paise": 149900, "status": "refunded", "invoice_url": "https://rzp.io/i/new", "invoice_id": "inv_new", "payment_id": "pay_b"}
            assert rows[1]["status"] == "paid" and rows[1]["invoice_url"] == "https://rzp.io/i/old"
    finally:
        await _cleanup(email)
