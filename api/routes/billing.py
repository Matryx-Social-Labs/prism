"""Billing: plans, checkout, verification, the subscription's life, the webhook.

Razorpay Subscriptions (UPI Autopay + cards). The flow: `/billing/checkout`
creates the subscription server-side at the price of the day and hands its id
to Checkout.js; Checkout's success callback comes back to `/billing/verify`
with Razorpay's signature, which turns the row active at once; the webhook
then keeps the row true over the months (charged, halted, cancelled). Until
the keys are set, `plans` says `checkout_ready: false` and the checkout routes
answer 503, so the pricing page shows no button that cannot work. Entitlement
is read from `subscriptions` by common/billing.plan_for.

The life after paying, each one click from the account page (DESIGN.md
§ Account): cancel (at cycle end, with an optional reason), pause (1–3 months,
resumed by the worker), a yearly plan that starts when the paid month ends,
the seven-day refund, and the payment history with Razorpay's invoices.
Two rules hold throughout: the reader is never charged twice for the same
days, and cancelling is never harder than subscribing was (CCPA dark-pattern
guidelines 2023: a "subscription trap" is an offence).
"""
from __future__ import annotations

import hashlib
import hmac
import uuid
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import get_current_user
from common import razorpay
from common.billing import OFFER, REGULAR, offer_open, prices
from common.billing_emails import notify_cancel_scheduled, notify_paused, notify_refund
from common.config import get_settings
from common.db import get_db
from common.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

SUBSCRIBED = ("active", "past_due", "paused")
CANCEL_REASONS = ("not-using", "too-expensive", "missing-something", "other")
PAUSE_MONTHS = (1, 2, 3)


def _launch_date() -> datetime | None:
    raw = get_settings().prism_paid_launch_date
    return datetime.fromisoformat(raw).replace(tzinfo=UTC) if raw else None


def _iso(d: datetime | None) -> str | None:
    return d.isoformat() if d else None


@router.get("/api/v1/billing/plans")
async def plans(db: AsyncSession = Depends(get_db)):
    out = await prices(db, _launch_date())
    out["checkout_ready"] = razorpay.configured()
    out["key_id"] = get_settings().razorpay_key_id or None  # public by design; Checkout.js needs it
    return out


class CheckoutIn(BaseModel):
    plan: str  # plus_monthly | plus_yearly | founding
    # From the cancel sheet: a yearly plan that begins the day the paid month
    # ends, replacing it — nothing is charged twice for the same days.
    start_after_current: bool = False


@router.post("/api/v1/billing/checkout")
async def checkout(body: CheckoutIn, db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """A subscription at TODAY's price for this plan, ready for Checkout.js."""
    if not razorpay.configured():
        raise HTTPException(status_code=503, detail="payments not configured")
    current = await _current(db, user_id)
    start_at: int | None = None
    replaces: str | None = None
    if current and current["status"] in SUBSCRIBED:
        switching = (
            body.start_after_current
            and body.plan in ("plus_yearly", "founding")
            and current["plan"] == "plus_monthly"
            and current["status"] == "active"
            and current["current_period_end"] is not None
            and current["provider"] == "razorpay"
        )
        if not switching:
            raise HTTPException(status_code=409, detail={"error": "already subscribed", "plan": current["plan"]})
        if await _scheduled(db, user_id):
            raise HTTPException(status_code=409, detail={"error": "a plan is already scheduled", "plan": current["plan"]})
        start_at = int(current["current_period_end"].timestamp())
        replaces = current["provider_sub_id"]
    on_offer = await offer_open(db, _launch_date())
    table = OFFER if on_offer else REGULAR
    price = table.get(body.plan)
    if price is None:
        raise HTTPException(status_code=422, detail=f"plan '{body.plan}' is not on sale")
    if body.plan == "founding" and (await prices(db, _launch_date()))["founding_left"] <= 0:
        raise HTTPException(status_code=422, detail="founding memberships are taken")
    spec = razorpay.PlanSpec(key=body.plan if on_offer else f"{body.plan}_regular", label=price.label, paise=price.paise, period=price.period)
    try:
        sub = await razorpay.create_subscription(spec, str(user_id), start_at=start_at, replaces=replaces)
    except Exception:
        logger.exception("razorpay_create_subscription_failed", user_id=str(user_id), plan=body.plan)
        raise HTTPException(status_code=502, detail="payment provider unavailable") from None
    await db.execute(
        text(
            """
            INSERT INTO subscriptions (id, user_id, provider, provider_sub_id, plan, status, price_paise, notes, starts_at)
            VALUES (:id, :u, 'razorpay', :sid, :plan, 'created', :price, 'checkout opened', :starts_at)
            ON CONFLICT (provider, provider_sub_id) DO NOTHING
            """
        ),
        {
            "id": uuid.uuid4(),
            "u": str(user_id),
            "sid": sub["id"],
            "plan": body.plan,
            "price": price.paise,
            "starts_at": datetime.fromtimestamp(start_at, tz=UTC) if start_at else None,
        },
    )
    return {
        "subscription_id": sub["id"],
        "key_id": get_settings().razorpay_key_id,
        "plan": body.plan,
        "label": price.label,
        "amount_paise": price.paise,
        "period": price.period,
        "starts_at": _iso(datetime.fromtimestamp(start_at, tz=UTC)) if start_at else None,
    }


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
        replaces = (sub.get("notes") or {}).get("replaces")
        if replaces:
            await _stop_replaced(db, user_id, replaces)
    except Exception:
        logger.exception("razorpay_fetch_after_verify_failed", sub=body.razorpay_subscription_id)
        await db.execute(
            text("UPDATE subscriptions SET status = 'active', notes = 'verified at checkout (unfetched)', updated_at = now() WHERE provider = 'razorpay' AND provider_sub_id = :sid"),
            {"sid": body.razorpay_subscription_id},
        )
        status = "active"
    return {"ok": True, "plan": owned, "status": status, "entitled": status in ("active", "past_due")}


async def _stop_replaced(db: AsyncSession, user_id: UUID, old_sid: str) -> None:
    """The yearly is authorised: the monthly it replaces stops at its cycle end."""
    old = (
        await db.execute(
            text("SELECT id, current_period_end FROM subscriptions WHERE provider = 'razorpay' AND provider_sub_id = :sid AND user_id = :u"),
            {"sid": old_sid, "u": str(user_id)},
        )
    ).mappings().first()
    if not old:
        return
    try:
        await razorpay.cancel_subscription(old_sid)
    except razorpay.NothingToCancel:
        pass
    except Exception:
        logger.exception("razorpay_cancel_replaced_failed", sub=old_sid)
    await db.execute(
        text("UPDATE subscriptions SET cancel_at = COALESCE(cancel_at, :at), notes = 'replaced by a yearly plan', updated_at = now() WHERE id = :id"),
        {"id": old["id"], "at": old["current_period_end"] or datetime.now(UTC)},
    )


class CancelIn(BaseModel):
    reason: str | None = None  # one of CANCEL_REASONS, optional — never required to leave
    comment: str | None = None


@router.post("/api/v1/billing/cancel")
async def cancel(body: CancelIn | None = None, db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """One click: stops the next charge; Plus stays on to the end of the paid period."""
    current = await _current(db, user_id)
    if not current or current["status"] not in ("active", "past_due", "paused"):
        raise HTTPException(status_code=404, detail="no active subscription")
    access_until = current["current_period_end"]
    if current["provider"] == "razorpay" and current["provider_sub_id"]:
        try:
            if current["status"] == "paused":
                # Razorpay cancels a paused subscription at once; the paid time
                # is already the reader's, so the date below is unchanged.
                await razorpay.cancel_subscription(current["provider_sub_id"], at_cycle_end=False)
            else:
                sub = await razorpay.cancel_subscription(current["provider_sub_id"])
                access_until = razorpay.period_end(sub) or access_until
        except razorpay.NothingToCancel:
            # Razorpay: "not cancellable in completed status" — every charge is
            # already made and none will follow. There is nothing to stop; the
            # reader keeps what they paid for and the row records that.
            pass
        except Exception:
            logger.exception("razorpay_cancel_failed", sub=current["provider_sub_id"])
            raise HTTPException(status_code=502, detail="payment provider unavailable") from None
    reason = body.reason if body and body.reason in CANCEL_REASONS else None
    comment = (body.comment or "").strip()[:280] if body else ""
    note = "cancelled by reader" + (f" · {reason}" if reason else "") + (f" · {comment}" if comment else "")
    await db.execute(
        text("UPDATE subscriptions SET cancel_at = :at, notes = :note, updated_at = now() WHERE id = :id"),
        {"id": current["id"], "at": access_until or datetime.now(UTC), "note": note},
    )
    await db.commit()
    logger.info("billing_cancel", plan=current["plan"], reason=reason, had_comment=bool(comment))
    try:
        await notify_cancel_scheduled(db, str(user_id), plan_key=current["plan"], price_paise=current["price_paise"], access_until=access_until)
    except Exception:
        logger.exception("cancel_email_failed", sub=current["provider_sub_id"])
    return {"ok": True, "access_until": _iso(access_until)}


class PauseIn(BaseModel):
    months: int = 1


@router.post("/api/v1/billing/pause")
async def pause(body: PauseIn, db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """The cancel sheet's first offer: no charges for one to three months after
    the paid period, then the plan comes back on its own (worker: resume_due).
    Razorpay pauses at once; the paid time stays the reader's by date."""
    if body.months not in PAUSE_MONTHS:
        raise HTTPException(status_code=422, detail="pause is one, two or three months")
    current = await _current(db, user_id)
    if not current or current["status"] != "active" or current["provider"] != "razorpay" or not current["provider_sub_id"]:
        raise HTTPException(status_code=409, detail="nothing to pause")
    if current["cancel_at"] or current["plan"] != "plus_monthly":
        raise HTTPException(status_code=409, detail="only a renewing monthly plan can be paused")
    try:
        await razorpay.pause_subscription(current["provider_sub_id"])
    except razorpay.PauseUnavailable as e:
        logger.warning("razorpay_pause_unavailable", sub=current["provider_sub_id"], detail=str(e)[:120])
        raise HTTPException(status_code=409, detail="pausing is not available on this plan yet") from None
    except Exception:
        logger.exception("razorpay_pause_failed", sub=current["provider_sub_id"])
        raise HTTPException(status_code=502, detail="payment provider unavailable") from None
    base = current["current_period_end"] or datetime.now(UTC)
    until = base + timedelta(days=30 * body.months)
    await db.execute(
        text("UPDATE subscriptions SET status = 'paused', paused_until = :until, notes = :note, updated_at = now() WHERE id = :id"),
        {"id": current["id"], "until": until, "note": f"paused by reader · {body.months} month(s)"},
    )
    await db.commit()
    logger.info("billing_pause", plan=current["plan"], months=body.months)
    try:
        await notify_paused(db, str(user_id), plan_key=current["plan"], price_paise=current["price_paise"], paid_until=current["current_period_end"], resumes=until)
    except Exception:
        logger.exception("pause_email_failed", sub=current["provider_sub_id"])
    return {"ok": True, "paused_until": until.isoformat(), "paid_until": _iso(current["current_period_end"])}


@router.post("/api/v1/billing/resume")
async def resume(db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """Back on before the chosen date: Razorpay resumes and charges on its next cycle."""
    current = await _current(db, user_id)
    if not current or current["status"] != "paused" or current["provider"] != "razorpay" or not current["provider_sub_id"]:
        raise HTTPException(status_code=409, detail="nothing to resume")
    try:
        sub = await razorpay.resume_subscription(current["provider_sub_id"])
    except Exception:
        logger.exception("razorpay_resume_failed", sub=current["provider_sub_id"])
        raise HTTPException(status_code=502, detail="payment provider unavailable") from None
    _, before, after = await razorpay.apply_subscription(db, sub, note="resumed by reader")
    await db.commit()
    if before != after:
        await razorpay.on_transition(db, str(user_id), before, after, sub)
    return {"ok": True, "status": after}


@router.post("/api/v1/billing/refund")
async def refund(db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """The Refund policy's seven days, as one click: the latest charge goes back
    in full to the instrument it was paid with and Plus ends at once. Order of
    operations is the safety: refund first, record it, then cancel — so a
    webhook racing the cancel finds `refund_id` already set and sends nothing
    on top of the refund email, and a failed cancel is caught by the reconcile
    while the reader already has their money."""
    current = await _current(db, user_id)
    until = razorpay.refundable_until(current["plan"], current["status"], current["current_period_start"], current["refund_id"]) if current else None
    if not current or not until or until < datetime.now(UTC):
        raise HTTPException(status_code=409, detail="no refund is open on this plan")
    if current["provider"] != "razorpay" or not current["provider_sub_id"]:
        raise HTTPException(status_code=409, detail="this plan was not paid through Razorpay; write to us")
    try:
        invoice = await razorpay.latest_paid_invoice(current["provider_sub_id"])
        if not invoice:
            raise HTTPException(status_code=409, detail="no paid charge found on this subscription")
        amount = int(invoice.get("amount_paid") or invoice.get("amount") or 0)
        rf = await razorpay.refund_payment(
            invoice["payment_id"], amount, notes={"user_id": str(user_id), "reason": "7-day refund policy", "subscription_id": current["provider_sub_id"]}
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("razorpay_refund_failed", sub=current["provider_sub_id"])
        raise HTTPException(status_code=502, detail="payment provider unavailable") from None
    now = datetime.now(UTC)
    await db.execute(
        text(
            "UPDATE subscriptions SET refund_id = :r, status = 'cancelled', cancel_at = :now, current_period_end = :now, "
            "notes = 'refunded by reader', updated_at = now() WHERE id = :id"
        ),
        {"id": current["id"], "r": rf["id"], "now": now},
    )
    await db.commit()
    try:
        await razorpay.cancel_subscription(current["provider_sub_id"], at_cycle_end=False)
    except razorpay.NothingToCancel:
        pass
    except Exception:
        logger.exception("razorpay_cancel_after_refund_failed", sub=current["provider_sub_id"], refund=rf["id"])
    logger.info("razorpay_refund", sub=current["provider_sub_id"], refund=rf["id"], amount=amount)
    try:
        await notify_refund(db, str(user_id), plan_key=current["plan"], amount_paise=amount, refund_id=rf["id"], ended=now)
    except Exception:
        logger.exception("refund_email_failed", refund=rf["id"])
    return {"ok": True, "refund_id": rf["id"], "amount_paise": amount, "ended_at": now.isoformat()}


@router.get("/api/v1/billing/me")
async def me(db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """The account page's plan row, and the plan scheduled after it if any."""
    current = await _current(db, user_id)
    if not current:
        return {"plan": "free"}
    until = razorpay.refundable_until(current["plan"], current["status"], current["current_period_start"], current["refund_id"])
    nxt = await _scheduled(db, user_id)
    return {
        "plan": current["plan"],
        "status": current["status"],
        "current_period_end": _iso(current["current_period_end"]),
        "cancel_at": _iso(current["cancel_at"]),
        "price_paise": current["price_paise"],
        "refundable_until": _iso(until),
        "refund_id": current["refund_id"],
        "paused_until": _iso(current["paused_until"]),
        "next": {"plan": nxt["plan"], "starts_at": _iso(nxt["starts_at"]), "price_paise": nxt["price_paise"]} if nxt else None,
    }


@router.get("/api/v1/billing/history")
async def history(db: AsyncSession = Depends(get_db), user_id: UUID = Depends(get_current_user)):
    """Every charge on the account, newest first, with Razorpay's hosted
    invoice (view, download as PDF). Read live from Razorpay: the invoice is
    theirs, and a cached copy could disagree with the one in the reader's inbox."""
    rows = (
        await db.execute(
            text("SELECT provider_sub_id, plan, refund_id FROM subscriptions WHERE user_id = :u AND provider = 'razorpay' AND provider_sub_id IS NOT NULL"),
            {"u": str(user_id)},
        )
    ).all()
    out = []
    for sid, plan, refund_id in rows:
        try:
            invoices = await razorpay.list_invoices(sid)
        except Exception:
            logger.exception("razorpay_invoices_failed", sub=sid)
            raise HTTPException(status_code=502, detail="payment provider unavailable") from None
        paid = [i for i in invoices if i.get("status") == "paid"]
        for i in paid:
            ts = int(i.get("paid_at") or i.get("issued_at") or 0)
            out.append(
                {
                    "paid_at": datetime.fromtimestamp(ts, tz=UTC).isoformat() if ts else None,
                    "plan": plan,
                    "amount_paise": int(i.get("amount_paid") or i.get("amount") or 0),
                    # One refund per subscription in our model, and it ends the
                    # plan — so the refunded charge is the latest paid one.
                    "status": "refunded" if refund_id and i is paid[0] else "paid",
                    "invoice_url": i.get("short_url"),
                    "invoice_id": i.get("id"),
                    "payment_id": i.get("payment_id"),
                }
            )
    out.sort(key=lambda x: x["paid_at"] or "", reverse=True)
    return {"payments": out}


async def _current(db: AsyncSession, user_id: UUID) -> dict | None:
    """The row that speaks for the reader now: a running plan before a
    scheduled one, a live plan before a dead one, newest otherwise."""
    row = (
        await db.execute(
            text(
                """
                SELECT id, provider, provider_sub_id, plan, status, current_period_start, current_period_end, cancel_at,
                       price_paise, refund_id, paused_until, starts_at
                FROM subscriptions WHERE user_id = :u
                ORDER BY (status IN ('active','past_due','paused') AND (starts_at IS NULL OR current_period_start IS NOT NULL)) DESC,
                         (status IN ('active','past_due','paused')) DESC, created_at DESC
                LIMIT 1
                """
            ),
            {"u": str(user_id)},
        )
    ).mappings().first()
    return dict(row) if row else None


async def _scheduled(db: AsyncSession, user_id: UUID) -> dict | None:
    """A plan authorised to begin later (the yearly taken from the cancel sheet)."""
    row = (
        await db.execute(
            text(
                "SELECT plan, starts_at, price_paise FROM subscriptions WHERE user_id = :u AND status = 'active' "
                "AND starts_at IS NOT NULL AND current_period_start IS NULL AND starts_at > now() ORDER BY created_at DESC LIMIT 1"
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
            logger.exception("razorpay_webhook_fetch_failed", kind=event, sub=sid)
            return {"ok": True, "ignored": "fetch failed"}
    if not (sub.get("notes") or {}).get("user_id"):
        logger.warning("razorpay_webhook_no_user", kind=event, sub=sub.get("id"))
        return {"ok": True, "ignored": "no user_id in notes"}
    user_id, before, after = await razorpay.apply_subscription(db, sub, note=event)
    # `event` is structlog's positional name; a kwarg of that name raised a
    # TypeError and 500'd every delivery (2026-09-20) — Razorpay retries, then
    # gives up on a webhook that keeps failing.
    logger.info("razorpay_webhook", kind=event, sub=sub.get("id"), before=before, after=after)
    if user_id and before != after:
        await razorpay.on_transition(db, user_id, before, after, sub)
    return {"ok": True, "status": after}
