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
    "plus_yearly": 1,
    "founding": 3,
    "plus_monthly_regular": 120,
    "plus_yearly_regular": 10,
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


async def cancel_subscription(sub_id: str, client: httpx.AsyncClient | None = None) -> dict[str, Any]:
    """Stop at the end of the paid period; access continues until then."""
    own = client is None
    client = client or _client()
    try:
        r = await client.post(f"/subscriptions/{sub_id}/cancel", json={"cancel_at_cycle_end": 1})
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
