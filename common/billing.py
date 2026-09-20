"""Plans, prices and entitlement — the one place that answers "what is this
reader allowed", read by Ask, the lens gate and /auth/me.

The provider is not wired yet (no Razorpay account on 2026-09-20). Rows arrive
two ways: `provider='manual'` written by tools/grant_plan.py for testers and
founding members, and later `provider='razorpay'` from the webhook. Entitlement
is computed from status + period end at read time, so a lapsed subscription
lapses without a job.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

FREE = "free"
PLUS = "plus"
# Days after a failed charge during which Plus stays on (dunning window).
GRACE = timedelta(days=3)


@dataclass(frozen=True)
class Price:
    plan: str
    label: str
    paise: int  # inclusive of GST, as shown
    period: str  # month | year


# The offer (PLAN-LAUNCH.md §1): ₹149/month until 90 days after the paid launch
# or the first 1,000 Plus subscribers, whichever first; those who join keep the
# price for 12 months. Regular prices apply after. The launch date is set the
# day payments go live (PRISM_PAID_LAUNCH_DATE); until then the offer is on.
OFFER = {
    "plus_monthly": Price("plus_monthly", "Plus · monthly", 14900, "month"),
    "plus_yearly": Price("plus_yearly", "Plus · yearly", 119900, "year"),
    "founding": Price("founding", "Founding member · yearly, price locked 3 years", 99900, "year"),
}
REGULAR = {
    "plus_monthly": Price("plus_monthly", "Plus · monthly", 19900, "month"),
    "plus_yearly": Price("plus_yearly", "Plus · yearly", 149900, "year"),
}
OFFER_DAYS = 90
OFFER_SUBSCRIBER_CAP = 1000
FOUNDING_CAP = 500

ENTITLED_STATUSES = {"active", "past_due"}


def entitled(status: str, current_period_end: datetime | None, now: datetime | None = None) -> bool:
    """Plus is on while the provider says active, and for GRACE after a failed
    charge (past_due) so a card hiccup does not lock a reader out mid-story."""
    now = now or datetime.now(UTC)
    if status == "active":
        return current_period_end is None or current_period_end + GRACE > now
    if status == "paused":
        # Paid time is kept; nothing after it until the worker resumes the plan.
        return current_period_end is not None and current_period_end > now
    if status == "past_due":
        return current_period_end is not None and current_period_end + GRACE > now
    return False


async def plan_for(session: AsyncSession, user_id: UUID | None) -> str:
    """'plus' or 'free' for this reader; anonymous is free."""
    if user_id is None:
        return FREE
    rows = (
        await session.execute(
            text("SELECT status, current_period_end FROM subscriptions WHERE user_id = :u ORDER BY created_at DESC"),
            {"u": user_id},
        )
    ).all()
    return PLUS if any(entitled(s, e) for s, e in rows) else FREE


async def offer_open(session: AsyncSession, launch_date: datetime | None) -> bool:
    """The launch offer is open until OFFER_DAYS after the paid launch or the
    first OFFER_SUBSCRIBER_CAP paying subscribers, whichever comes first."""
    if launch_date and datetime.now(UTC) > launch_date + timedelta(days=OFFER_DAYS):
        return False
    n = (await session.execute(text("SELECT count(*) FROM subscriptions WHERE provider <> 'manual' AND status IN ('active','past_due')"))).scalar() or 0
    return n < OFFER_SUBSCRIBER_CAP


async def prices(session: AsyncSession, launch_date: datetime | None) -> dict:
    """What the pricing page shows: the offer while it is open, with its end."""
    on_offer = await offer_open(session, launch_date)
    founding_left = FOUNDING_CAP - ((await session.execute(text("SELECT count(*) FROM subscriptions WHERE plan = 'founding' AND status IN ('active','past_due')"))).scalar() or 0)
    table = dict(OFFER) if on_offer else dict(REGULAR)
    if not on_offer or founding_left <= 0:
        table.pop("founding", None)
    return {
        "offer": on_offer,
        "offer_ends": (launch_date + timedelta(days=OFFER_DAYS)).isoformat() if launch_date else None,
        "founding_left": max(founding_left, 0),
        "plans": [{"plan": p.plan, "label": p.label, "amount_paise": p.paise, "period": p.period} for p in table.values()],
    }
