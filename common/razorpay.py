"""Razorpay Subscriptions, the little of it Prism needs (BUSINESS-MODEL.md §8).

Plain httpx against https://api.razorpay.com/v1 with key basic-auth — no SDK
for four calls. Plans are found or created on demand by a `notes.key` we set,
so there is no plan-id configuration to keep in step across test and live
accounts: switch the keys and the first checkout makes the plans.

Nothing here decides prices: common/billing.py does, and passes the paise in.
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from typing import Any

import httpx

from common.config import get_settings

BASE = "https://api.razorpay.com/v1"

# Charges a subscription runs before it completes. The offer price is kept
# for twelve monthly charges; a completed subscription is re-offered at the
# price of the day (never silently stepped up). Founding: three yearly charges
# at the locked price. Regular plans run until cancelled (Razorpay needs a
# count; ten years is "until cancelled").
TOTAL_COUNT = {
    "plus_monthly": 12,
    # NOT 1: a one-charge subscription is "completed" the moment it is paid and
    # never "active" (that is how the first real test purchase read as expired,
    # 2026-09-21). The yearly offer renews at the same price; ten years is
    # "until cancelled".
    "plus_yearly": 10,
    "founding": 3,
    "plus_monthly_regular": 120,
    "plus_yearly_regular": 10,
}

# Razorpay subscription status → ours (common/billing.entitled reads ours).
# `completed` — every charge in total_count made — is still PAID UP to
# current_end, so it stays active; entitlement lapses by the date, not the word.
STATUS = {
    "created": "created",
    "authenticated": "active",
    "active": "active",
    "pending": "past_due",
    "halted": "halted",
    "cancelled": "cancelled",
    "completed": "active",
    "expired": "expired",
    "paused": "cancelled",
}
PERIOD = {"month": "monthly", "year": "yearly"}


@dataclass(frozen=True)
class PlanSpec:
    key: str  # plus_monthly | plus_yearly | founding, with _regular when off the offer
    label: str
    paise: int
    period: str  # month | year


def configured() -> bool:
    s = get_settings()
    return bool(s.razorpay_key_id and s.razorpay_key_secret)


def _client() -> httpx.AsyncClient:
    s = get_settings()
    return httpx.AsyncClient(base_url=BASE, auth=(s.razorpay_key_id, s.razorpay_key_secret), timeout=20)


_plan_cache: dict[str, str] = {}


async def ensure_plan(spec: PlanSpec, client: httpx.AsyncClient | None = None) -> str:
    """The Razorpay plan id for this price, created on first use.

    Matched by our `notes.key` AND the amount, so a price change makes a new
    plan rather than silently charging the old figure."""
    if spec.key in _plan_cache:
        return _plan_cache[spec.key]
    own = client is None
    client = client or _client()
    try:
        r = await client.get("/plans", params={"count": 100})
        r.raise_for_status()
        for p in r.json().get("items", []):
            if (p.get("notes") or {}).get("key") == spec.key and (p.get("item") or {}).get("amount") == spec.paise:
                _plan_cache[spec.key] = p["id"]
                return p["id"]
        r = await client.post(
            "/plans",
            json={
                "period": PERIOD[spec.period],
                "interval": 1,
                "item": {"name": f"Prism {spec.label}", "amount": spec.paise, "currency": "INR"},
                "notes": {"key": spec.key},
            },
        )
        r.raise_for_status()
        _plan_cache[spec.key] = r.json()["id"]
        return _plan_cache[spec.key]
    finally:
        if own:
            await client.aclose()


async def create_subscription(spec: PlanSpec, user_id: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """A subscription awaiting its first payment; the id goes to Checkout."""
    own = client is None
    client = client or _client()
    try:
        plan_id = await ensure_plan(spec, client)
        r = await client.post(
            "/subscriptions",
            json={
                "plan_id": plan_id,
                "total_count": TOTAL_COUNT[spec.key],
                "customer_notify": 1,
                # Read back by the webhook (api/routes/billing.py): whose
                # subscription, which plan, at what price.
                "notes": {"user_id": user_id, "plan": spec.key.removesuffix("_regular"), "price_paise": str(spec.paise)},
            },
        )
        r.raise_for_status()
        return r.json()
    finally:
        if own:
            await client.aclose()


class NothingToCancel(Exception):
    """Razorpay refused the cancel because the subscription has already run its course."""


async def cancel_subscription(sub_id: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Stop at the end of the paid period; access continues until then."""
    own = client is None
    client = client or _client()
    try:
        r = await client.post(f"/subscriptions/{sub_id}/cancel", json={"cancel_at_cycle_end": 1})
        if r.status_code == 400 and "not cancellable" in r.text:
            raise NothingToCancel(r.text[:200])
        r.raise_for_status()
        return r.json()
    finally:
        if own:
            await client.aclose()


def verify_checkout_signature(payment_id: str, subscription_id: str, signature: str) -> bool:
    """Checkout's success callback is trusted only with Razorpay's HMAC over
    `payment_id|subscription_id`, keyed by the secret the browser never sees."""
    secret = get_settings().razorpay_key_secret
    if not secret:
        return False
    expected = hmac.new(secret.encode(), f"{payment_id}|{subscription_id}".encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature or "")


async def fetch_subscription(sub_id: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Razorpay's own record of a subscription — the truth the row is kept to."""
    own = client is None
    client = client or _client()
    try:
        r = await client.get(f"/subscriptions/{sub_id}")
        r.raise_for_status()
        return r.json()
    finally:
        if own:
            await client.aclose()


def period_end(sub: dict[str, Any]):
    """When the paid period ends: `current_end` while it runs, `ended_at`/`end_at` after."""
    from datetime import UTC, datetime

    for key in ("current_end", "end_at", "ended_at"):
        v = sub.get(key)
        if v:
            return datetime.fromtimestamp(int(v), tz=UTC)
    return None


async def apply_subscription(db, sub: dict[str, Any], *, note: str) -> tuple[str | None, str, str]:
    """Write Razorpay's subscription onto our row; returns (user_id, before, after).

    One function for the three ways the truth arrives — Checkout's verified
    callback, the webhook, and the hourly reconcile — so no path can disagree
    with another. Never demotes an entitled reader on a missing row."""
    import uuid as _uuid

    from sqlalchemy import text

    notes = sub.get("notes") or {}
    user_id = notes.get("user_id")
    if not user_id:
        return None, "", ""
    status = STATUS.get(sub.get("status", ""), "cancelled")
    end = period_end(sub)
    before = (
        await db.execute(
            text("SELECT status FROM subscriptions WHERE provider = 'razorpay' AND provider_sub_id = :sid"),
            {"sid": sub["id"]},
        )
    ).scalar_one_or_none() or ""
    # When no further charge will come — cancelled, or every charge made
    # (`completed`) — the end date is recorded as cancel_at: the plan card then
    # says "Ends <date> · no further charges" and offers nothing to cancel.
    cancel_at = None
    if sub.get("status") in ("cancelled", "completed") or (sub.get("status") in ("active", "authenticated") and sub.get("end_at") and int(sub.get("remaining_count") or 1) == 0):
        cancel_at = end
    await db.execute(
        text(
            """
            INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, current_period_end, cancel_at, price_paise, notes)
            VALUES (:id, :u, 'razorpay', :sid, :plan, :status, :end, :cancel_at, :price, :notes)
            ON CONFLICT (provider, provider_sub_id) DO UPDATE SET
              status = EXCLUDED.status, current_period_end = EXCLUDED.current_period_end,
              cancel_at = COALESCE(EXCLUDED.cancel_at, subscriptions.cancel_at),
              plan = EXCLUDED.plan, price_paise = COALESCE(EXCLUDED.price_paise, subscriptions.price_paise),
              notes = EXCLUDED.notes, updated_at = now()
            """
        ),
        {
            "id": _uuid.uuid4(),
            "u": user_id,
            "sid": sub["id"],
            "plan": notes.get("plan") or "plus_monthly",
            "status": status,
            "end": end,
            "cancel_at": cancel_at,
            "price": int(notes["price_paise"]) if notes.get("price_paise") else None,
            "notes": note,
        },
    )
    return user_id, before, status


async def reconcile_pending(db) -> int:
    """Ask Razorpay about every row the webhook may have missed: checkouts
    still 'created' after two minutes, and entitled rows not touched in a day.
    Returns how many rows changed status."""
    from sqlalchemy import text

    if not configured():
        return 0
    rows = (
        await db.execute(
            text(
                """
                SELECT provider_sub_id FROM subscriptions
                WHERE provider = 'razorpay' AND provider_sub_id IS NOT NULL
                  AND ((status = 'created' AND created_at < now() - interval '2 minutes' AND created_at > now() - interval '7 days')
                       OR (status IN ('active','past_due') AND updated_at < now() - interval '1 day'))
                LIMIT 200
                """
            )
        )
    ).scalars().all()
    changed = 0
    async with _client() as client:
        for sid in rows:
            try:
                sub = await fetch_subscription(sid, client)
            except Exception:
                continue
            user_id, before, after = await apply_subscription(db, sub, note="reconciled")
            if user_id and before != after:
                changed += 1
                await on_transition(db, user_id, before, after, sub)
    return changed


async def on_transition(db, user_id: str, before: str, after: str, sub: dict[str, Any]) -> None:
    """The emails a status change owes the reader (common/billing_emails)."""
    from common.billing_emails import notify_transition

    try:
        await notify_transition(db, user_id, before, after, sub)
    except Exception:  # an email must never fail a payment
        import logging

        logging.getLogger(__name__).exception("billing_email_failed")
