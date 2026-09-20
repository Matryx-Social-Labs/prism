"""Billing: plans, checkout, verification, cancellation, and the webhook.

Razorpay Subscriptions (UPI Autopay + cards). The flow: `/billing/checkout`
creates the subscription server-side at the price of the day and hands its id
to Checkout.js; Checkout's success callback comes back to `/billing/verify`
with Razorpay's signature, which turns the row active at once; the webhook
then keeps the row true over the months (charged, halted, cancelled). Until
the keys are set, `plans` says `checkout_ready: false` and the checkout routes
answer 503, so the pricing page shows no button that cannot work. Entitlement
is read from `subscriptions` by common/billing.plan_for.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from common import razorpay
from common.billing import OFFER, REGULAR, offer_open, prices
from common.config import get_settings
from common.db import get_db
from common.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

def _launch_date() -> datetime | None:
    raw = get_settings().prism_paid_launch_date
    return datetime.fromisoformat(raw).replace(tzinfo=UTC) if raw else None


@router.get("/api/v1/billing/plans")
async def plans(db: AsyncSession = Depends(get_db)):
    out = await prices(db, _launch_date())
    out["checkout_ready"] = razorpay.configured()
    out["key_id"] = get_settings().razorpay_key_id or None  # public by design; Checkout.js needs it
    return out


class CheckoutIn(BaseModel):
    plan: str  # plus_monthly | plus_yearly | founding


@router.post("/api/v1/billing/checkout")
async def checkout(body: CheckoutIn, db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """A subscription at TODAY's price for this plan, ready for Checkout.js."""
    if not razorpay.configured():
        raise HTTPException(status_code=503, detail="payments not configured")
    current = await _current(db, user_id)
    if current and current["status"] in ("active", "past_due"):
        raise HTTPException(status_code=409, detail={"error": "already subscribed", "plan": current["plan"]})
    on_offer = await offer_open(db, _launch_date())
    table = OFFER if on_offer else REGULAR
    price = table.get(body.plan)
    if price is None:
        raise HTTPException(status_code=422, detail=f"plan '{body.plan}' is not on sale")
    if body.plan == "founding" and (await prices(db, _launch_date()))["founding_left"] <= 0:
        raise HTTPException(status_code=422, detail="founding memberships are taken")
    spec = razorpay.PlanSpec(key=body.plan if on_offer else f"{body.plan}_regular", label=price.label, paise=price.paise, period=price.period)
    try:
        sub = await razorpay.create_subscription(spec, str(user_id))
    except Exception:
        logger.exception("razorpay_create_subscription_failed", user_id=str(user_id), plan=body.plan)
        raise HTTPException(status_code=502, detail="payment provider unavailable") from None
    await db.execute(
        text(
            """
            INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, price_paise, notes)
            VALUES (:id, :u, 'razorpay', :sid, :plan, 'created', :price, 'checkout opened')
            ON CONFLICT (provider, provider_sub_id) DO NOTHING
            """
        ),
        {"id": uuid.uuid4(), "u": str(user_id), "sid": sub["id"], "plan": body.plan, "price": price.paise},
    )
    return {"subscription_id": sub["id"], "key_id": get_settings().razorpay_key_id, "plan": body.plan, "label": price.label, "amount_paise": price.paise, "period": price.period}


class VerifyIn(BaseModel):
    razorpay_payment_id: str
    razorpay_subscription_id: str
    razorpay_signature: str


@router.post("/api/v1/billing/verify")
async def verify(body: VerifyIn, db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """Checkout's success callback: the signature proves the payment; the row
    turns active now rather than whenever the webhook lands."""
    if not razorpay.verify_checkout_signature(body.razorpay_payment_id, body.razorpay_subscription_id, body.razorpay_signature):
        raise HTTPException(status_code=400, detail="bad signature")
    owned = (
        await db.execute(
            text("SELECT plan FROM subscriptions WHERE provider = 'razorpay' AND provider_sub_id = :sid AND user_id = :u"),
            {"sid": body.razorpay_subscription_id, "u": str(user_id)},
        )
    ).scalar_one_or_none()
    if owned is None:
        raise HTTPException(status_code=404, detail="no such subscription for this account")
    # Razorpay's record is the truth: status, the paid period's end, the plan.
    # If Razorpay cannot be reached this second, the signature alone turns the
    # row active and the hourly reconcile fills the dates in.
    try:
        sub = await razorpay.fetch_subscription(body.razorpay_subscription_id)
        _, before, after = await razorpay.apply_subscription(db, sub, note="verified at checkout")
        if before != after:
            await razorpay.on_transition(db, str(user_id), before, after, sub)
        status = after
    except Exception:
        logger.exception("razorpay_fetch_after_verify_failed", sub=body.razorpay_subscription_id)
        await db.execute(
            text("UPDATE subscriptions SET status = 'active', notes = 'verified at checkout (unfetched)', updated_at = now() WHERE provider = 'razorpay' AND provider_sub_id = :sid"),
            {"sid": body.razorpay_subscription_id},
        )
        status = "active"
    return {"ok": True, "plan": owned, "status": status, "entitled": status in ("active", "past_due")}


@router.post("/api/v1/billing/cancel")
async def cancel(db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """One click: stops the next charge; Plus stays on to the end of the paid period."""
    current = await _current(db, user_id)
    if not current or current["status"] not in ("active", "past_due"):
        raise HTTPException(status_code=404, detail="no active subscription")
    access_until = current["current_period_end"]
    if current["provider"] == "razorpay" and current["provider_sub_id"]:
        try:
            sub = await razorpay.cancel_subscription(current["provider_sub_id"])
            access_until = razorpay.period_end(sub) or access_until
        except Exception:
            logger.exception("razorpay_cancel_failed", sub=current["provider_sub_id"])
            raise HTTPException(status_code=502, detail="payment provider unavailable") from None
    await db.execute(
        text("UPDATE subscriptions SET cancel_at = :at, notes = 'cancelled by reader', updated_at = now() WHERE id = :id"),
        {"id": current["id"], "at": access_until or datetime.now(UTC)},
    )
    return {"ok": True, "access_until": access_until.isoformat() if access_until else None}


@router.get("/api/v1/billing/me")
async def me(db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """The account page's plan row."""
    current = await _current(db, user_id)
    if not current:
        return {"plan": "free"}
    return {
        "plan": current["plan"],
        "status": current["status"],
        "current_period_end": current["current_period_end"].isoformat() if current["current_period_end"] else None,
        "cancel_at": current["cancel_at"].isoformat() if current["cancel_at"] else None,
        "price_paise": current["price_paise"],
    }


async def _current(db: AsyncSession, user_id: UUID) -> dict | None:
    row = (
        await db.execute(
            text(
                """
                SELECT id, provider, provider_sub_id, plan, status, current_period_end, cancel_at, price_paise
                FROM subscriptions WHERE user_id = :u
                ORDER BY (status IN ('active','past_due')) DESC, created_at DESC LIMIT 1
                """
            ),
            {"u": str(user_id)},
        )
    ).mappings().first()
    return dict(row) if row else None


@router.post("/api/v1/billing/razorpay/webhook")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    secret = get_settings().razorpay_webhook_secret
    if not secret:
        raise HTTPException(status_code=503, detail="billing provider not configured")
    body = await request.body()
    given = request.headers.get("x-razorpay-signature", "")
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(given, expected):
        raise HTTPException(status_code=401, detail="bad signature")
    payload = await request.json()
    event = payload.get("event", "")
    sub = ((payload.get("payload") or {}).get("subscription") or {}).get("entity") or {}
    if not sub.get("id"):
        # payment.* events carry the subscription id on the payment; fetch it.
        pay = ((payload.get("payload") or {}).get("payment") or {}).get("entity") or {}
        sid = pay.get("subscription_id") if isinstance(pay, dict) else None
        if not sid:
            return {"ok": True, "ignored": event}
        try:
            sub = await razorpay.fetch_subscription(sid)
        except Exception:
            logger.exception("razorpay_webhook_fetch_failed", event=event, sub=sid)
            return {"ok": True, "ignored": "fetch failed"}
    if not (sub.get("notes") or {}).get("user_id"):
        logger.warning("razorpay_webhook_no_user", event=event, sub=sub.get("id"))
        return {"ok": True, "ignored": "no user_id in notes"}
    user_id, before, after = await razorpay.apply_subscription(db, sub, note=event)
    logger.info("razorpay_webhook", event=event, sub=sub.get("id"), before=before, after=after)
    if user_id and before != after:
        await razorpay.on_transition(db, user_id, before, after, sub)
    return {"ok": True, "status": after}
