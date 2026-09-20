"""Billing: the plans the pricing page shows, and the provider webhook.

The provider is Razorpay Subscriptions (UPI Autopay + cards), not yet wired on
2026-09-20 — no account. This route is the plug-in point built ahead of it:
`/billing/plans` already serves the offer, and the webhook verifies Razorpay's
HMAC and writes `subscriptions` rows, returning 503 until the secret is set.
Entitlement is read from those rows by common/billing.plan_for; nothing else
needs to change when the account arrives except the checkout button.
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.billing import prices
from common.config import get_settings
from common.db import get_db
from common.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Razorpay subscription status → ours (common/billing.entitled reads ours).
STATUS = {
    "authenticated": "active",
    "active": "active",
    "pending": "past_due",
    "halted": "halted",
    "cancelled": "cancelled",
    "completed": "expired",
    "expired": "expired",
    "paused": "cancelled",
}


def _launch_date() -> datetime | None:
    raw = get_settings().prism_paid_launch_date
    return datetime.fromisoformat(raw).replace(tzinfo=UTC) if raw else None


@router.get("/api/v1/billing/plans")
async def plans(db: AsyncSession = Depends(get_db)):
    return await prices(db, _launch_date())


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
    if not event.startswith("subscription.") or not sub.get("id"):
        return {"ok": True, "ignored": event}
    notes = sub.get("notes") or {}
    user_id = notes.get("user_id")
    plan = notes.get("plan") or "plus_monthly"
    if not user_id:
        logger.warning("razorpay_webhook_no_user", event=event, sub=sub.get("id"))
        return {"ok": True, "ignored": "no user_id in notes"}
    period_end = sub.get("current_end")
    await db.execute(
        text(
            """
            INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, current_period_end, price_paise, notes)
            VALUES (:id, :u, 'razorpay', :sid, :plan, :status, :end, :price, :notes)
            ON CONFLICT (provider, provider_sub_id) DO UPDATE SET
              status = EXCLUDED.status, current_period_end = EXCLUDED.current_period_end, plan = EXCLUDED.plan, updated_at = now()
            """
        ),
        {
            "id": uuid.uuid4(),
            "u": user_id,
            "sid": sub["id"],
            "plan": plan,
            "status": STATUS.get(sub.get("status", ""), "cancelled"),
            "end": datetime.fromtimestamp(period_end, tz=UTC) if period_end else None,
            "price": notes.get("price_paise"),
            "notes": event,
        },
    )
    return {"ok": True}
