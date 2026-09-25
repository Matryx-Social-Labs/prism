"""The emails a subscription owes a reader, one per moment of its life:

  welcome            first charge verified (created/past_due/halted → active)
  charge failed      active → past_due (Razorpay retries for three days)
  cancel scheduled   the reader clicked Cancel — sent at once, from the route
  paused             the reader paused instead — from the route; "back on" when
                     it resumes (paused → active, by the worker or by hand)
  yearly scheduled   a yearly plan authorised to start when the month ends
  ended              the scheduled end arrived, or Razorpay cancelled/halted it
  refunded           the reader took the 7-day refund — sent from the route

Razorpay sends the receipt/invoice for every charge (customer_notify=1); these
are ours — what changed for them on Prism and what to do next. Same shell as
the sign-in email (common/email_templates), plain text first. Nothing here
raises into billing: a dropped email is logged, never a failed payment.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import text

from common.config import get_settings
from common.email import get_email_sender
from common.email_templates import IST, render
from common.quota import PLUS_ASK_PER_DAY, USER_ASK_PER_DAY
from common.razorpay import REFUND_DAYS, REFUNDABLE_PLANS, refundable_until

PLAN_LABEL = {"plus_monthly": "Plus · monthly", "plus_yearly": "Plus · yearly", "founding": "Founding member"}
PER = {"plus_monthly": "a month", "plus_yearly": "a year"}

# Razorpay charges, invoices and retries on IST — a cycle ends at 00:00 IST —
# so every date about money is the Indian calendar day, tagged IST, the same
# words the receipt uses (a reader in Berlin who paid at 20:50 on the 20th was
# charged on the 21st and is billed again on the 21st; the UTC date said the
# 20th, 2026-09-21). Dates in the meta line are the same day, untagged.

PLUS_IS = f"{PLUS_ASK_PER_DAY} questions a day, answered from the whole story"
FREE_KEEPS = f"The record stays free: every story, source, quote and clip, your watchlist, and {USER_ASK_PER_DAY} questions a day."


def _day(d: datetime | None, *, tag: bool = True) -> str | None:
    if not d:
        return None
    s = d.astimezone(IST).strftime("%-d %B %Y")
    return f"{s} IST" if tag else s


def _ts(ts: Any) -> datetime | None:
    return datetime.fromtimestamp(int(ts), tz=UTC) if ts else None


def rupees(paise: int | None) -> str | None:
    return f"₹{paise // 100:,}" if paise else None


def _meta(*parts: str | None) -> str:
    return " · ".join(x for x in parts if x)


def _plan_fact(plan: str, price: str | None) -> str:
    """Plus · yearly · ₹1,199 (GST included): every Prism price includes GST (the Plus page)."""
    return f"{plan} · {price} (GST included)" if price else plan


async def _send(
    db,
    user_id: str,
    *,
    subject: str,
    meta: str,
    lines: list[str],
    facts: list[tuple[str, str | None]],
    cta: tuple[str, str] | None,
    because: str,
    title: str | None = None,
    preheader: str | None = None,
) -> None:
    """`because` finishes "You are getting this because …" and may name {email}."""
    email = (await db.execute(text("SELECT email FROM users WHERE id = :u"), {"u": user_id})).scalar_one_or_none()
    if not email:
        return
    text_body, html = render(
        subject=subject,
        title=title or subject,
        meta=meta,
        paragraphs=[x for x in lines if x],
        facts=[(k, v) for k, v in facts if v],
        cta=cta,
        because=because.format(email=email),
        preheader=preheader,
    )
    await get_email_sender().send(to=email, subject=subject, body=text_body, html=html)


async def notify_transition(db, user_id: str, before: str, after: str, sub: dict[str, Any]) -> None:
    """The emails that follow a status change Razorpay reported."""
    web = get_settings().prism_web_url.rstrip("/")
    notes = sub.get("notes") or {}
    plan_key = notes.get("plan") or ""
    plan = PLAN_LABEL.get(plan_key, "Plus")
    price = rupees(int(notes["price_paise"])) if notes.get("price_paise") else None
    end = _ts(sub.get("current_end")) or _ts(sub.get("end_at")) or _ts(sub.get("ended_at"))
    now = datetime.now(UTC)
    today = _day(now, tag=False)
    meta = _meta(plan, price, today)

    if after == "active" and before == "paused":
        await _send(
            db,
            user_id,
            subject="Prism Plus is back on",
            meta=meta,
            lines=[f"Your pause has ended, and Plus is on again: {PLUS_IS}."],
            facts=[("Plan", _plan_fact(plan, price)), ("Next charge", _day(_ts(sub.get("charge_at"))) or _day(end))],
            cta=("Back to the record", f"{web}/feed"),
            because="the pause you set on Prism Plus ended, on {email}.",
            preheader="Your pause has ended. Plus is on again.",
        )
        return

    if after == "paused":
        return  # the route that paused it has already written

    starts = _ts(sub.get("start_at"))
    if after == "active" and before in ("", "created") and starts and not sub.get("current_start") and starts > now:
        first = f"{price} on {_day(starts)}." if price else f"On {_day(starts)}."
        if plan_key in REFUNDABLE_PLANS:
            first += f" Full refund within {REFUND_DAYS} days of it."
        await _send(
            db,
            user_id,
            subject="Your yearly Plus is set",
            meta=_meta(plan, price, f"starts {_day(starts, tag=False)}"),
            lines=[f"Your monthly Plus stays on until {_day(starts)}. Yearly starts then, and nothing is charged twice."],
            facts=[("Plan", _plan_fact(plan, price)), ("Starts", _day(starts)), ("First charge", first)],
            cta=("Your account", f"{web}/account"),
            because="you switched Prism Plus to yearly on {email}.",
            preheader=f"Monthly Plus runs to {_day(starts)}. Yearly starts then; nothing is charged twice.",
        )
        return

    if after == "active" and before in ("", "created", "past_due", "halted"):
        renews = _day(end) if sub.get("status") == "active" else None
        refund_until = refundable_until(plan_key, sub.get("status") or "", _ts(sub.get("current_start")), None)
        await _send(
            db,
            user_id,
            subject="You're on Prism Plus",
            meta=meta,
            lines=[f"Ask is on at {PLUS_IS}, on a larger model."],
            facts=[
                ("Plan", _plan_fact(plan, price)),
                ("Next charge", renews) if renews else ("Paid through", _day(end)),
                ("Receipt", "Razorpay emails it separately. It is also under Payments in your account."),
                (
                    "Changing your mind",
                    f"Full refund until {_day(refund_until)}, in one click from your account"
                    if refund_until
                    else "Cancel any time from your account; Plus stays on to the end of the time you paid for",
                ),
            ],
            cta=("Your account", f"{web}/account"),
            because="Plus started on your Prism account, {email}.",
            preheader=f"Plus is on: {PLUS_IS}.",
        )
        return

    if after == "past_due":
        await _send(
            db,
            user_id,
            subject="A Prism Plus charge did not go through",
            title="A charge did not go through",
            meta=meta,
            lines=[
                f"Razorpay could not take {price or 'the charge'} for Prism Plus, so nothing was charged. Plus stays on while Razorpay tries again.",
                "The email from Razorpay has a link to change your UPI or card.",
            ],
            facts=[
                ("Plan", _plan_fact(plan, price)),
                ("Plus stays on until", _day(end)),
                ("After that", "If no charge goes through, Plus pauses. Reading stays free."),
            ],
            cta=("Your account", f"{web}/account"),
            because="a charge for Prism Plus on {email} did not go through.",
            preheader="Nothing was charged. Plus stays on while Razorpay tries again.",
        )
        return

    if after in ("cancelled", "halted", "expired") and before in ("active", "past_due"):
        row = (
            await db.execute(
                text("SELECT cancel_at, refund_id FROM subscriptions WHERE provider = 'razorpay' AND provider_sub_id = :sid"),
                {"sid": sub.get("id")},
            )
        ).mappings().first()
        if row and row["refund_id"]:
            return  # the refund email already said everything this would
        scheduled = bool(row and row["cancel_at"])
        still_on = end is not None and end > now
        plus = ("Prism Plus", f"{web}/plus")
        if after == "halted":
            await _send(
                db,
                user_id,
                subject="Prism Plus is paused",
                meta=_meta(plan, f"paused {today}"),
                lines=[
                    "Razorpay tried the charge several times and none went through, so Plus is paused. Nothing more will be charged.",
                    f"{FREE_KEEPS} You can start Plus again at any time.",
                ],
                facts=[],
                cta=plus,
                because="Prism Plus on {email} paused after failed charges.",
                preheader="Repeated charges did not go through, so Plus is paused. Reading stays free.",
            )
        elif still_on and not scheduled:
            mandate = after == "cancelled"
            await _send(
                db,
                user_id,
                subject="Your Prism Plus will not renew",
                title="Your Plus will not renew",
                meta=_meta(plan, f"ends {_day(end, tag=False)}"),
                lines=[
                    ("The UPI Autopay or card mandate for Prism Plus was cancelled outside Prism, so it will not renew. " if mandate else "Your Prism Plus will not renew. ")
                    + f"You keep Plus until {_day(end)}.",
                    "If that was not you, you can start Plus again from the Plus page." if mandate else None,
                ],
                facts=[],
                cta=plus,
                because="the payment mandate for Prism Plus on {email} was cancelled." if mandate else "Prism Plus on {email} will not renew.",
                preheader=f"{'The payment mandate was cancelled outside Prism. ' if mandate else ''}You keep Plus until {_day(end)}.",
            )
        else:
            await _send(
                db,
                user_id,
                subject="Your Prism Plus has ended",
                title="Your Plus has ended",
                meta=_meta(plan, f"ended {_day(end, tag=False)}" if end else "ended"),
                lines=[f"Your Prism Plus ended{' on ' + _day(end) if end else ''}. No further charges.", FREE_KEEPS],
                facts=[],
                cta=plus,
                because="Prism Plus ended on {email}.",
                preheader=f"Plus ended{' on ' + _day(end) if end else ''}. The record stays free.",
            )


async def notify_cancel_scheduled(db, user_id: str, *, plan_key: str, price_paise: int | None, access_until: datetime | None) -> None:
    """The reader clicked Cancel: say at once what happens and when."""
    web = get_settings().prism_web_url.rstrip("/")
    plan = PLAN_LABEL.get(plan_key, "Plus")
    until = _day(access_until)
    await _send(
        db,
        user_id,
        subject="Your Prism Plus is set to end",
        title="Your Plus is set to end",
        meta=_meta(plan, f"ends {_day(access_until, tag=False)}") if access_until else _meta(plan, rupees(price_paise), _day(datetime.now(UTC), tag=False)),
        lines=["You cancelled Prism Plus. It stays on until the end of the time you paid for."],
        facts=[("Ends", until), ("Further charges", "None")],
        cta=("Your account", f"{web}/account"),
        because="you cancelled Prism Plus on {email}.",
        preheader=f"You keep Plus until {until}. No further charges." if until else "No further charges.",
    )


async def notify_paused(db, user_id: str, *, plan_key: str, price_paise: int | None, paid_until: datetime | None, resumes: datetime) -> None:
    """The reader paused instead of cancelling: what stays, what stops, when it returns."""
    web = get_settings().prism_web_url.rstrip("/")
    plan = PLAN_LABEL.get(plan_key, "Plus")
    price = rupees(price_paise)
    # The route pauses for 30 days a month from the paid period's end, so the
    # months are exact when that end is known (api/routes/billing.pause).
    months = (resumes - paid_until).days // 30 if paid_until else None
    span = f"{months} {'month' if months == 1 else 'months'}" if months else None
    per = PER.get(plan_key)
    await _send(
        db,
        user_id,
        subject="Prism Plus is paused",
        meta=_meta(plan, f"paused {span}" if span else f"resumes {_day(resumes, tag=False)}"),
        lines=[
            f"You paused Plus{' for ' + span if span else ''}. It stays on until the end of the time you paid for, then pauses.",
            "Want it back sooner? Resume from your account at any time.",
        ],
        facts=[
            ("Stays on until", _day(paid_until)),
            ("Charges", "None while paused"),
            ("Resumes", f"{_day(resumes)}, at {price} {per}" if price and per else _day(resumes)),
        ],
        cta=("Your account", f"{web}/account"),
        because="you paused Prism Plus on {email}.",
        preheader=(
            f"Plus stays on until {_day(paid_until)}, then pauses until {_day(resumes)}. No charges while paused."
            if paid_until
            else f"No charges until {_day(resumes)}."
        ),
    )


async def notify_refund(db, user_id: str, *, plan_key: str, amount_paise: int, refund_id: str, ended: datetime) -> None:
    """The 7-day refund went through: the amount, where it goes, and when."""
    web = get_settings().prism_web_url.rstrip("/")
    amount = rupees(amount_paise) or ""
    await _send(
        db,
        user_id,
        subject=f"Refunded: {amount} for Prism Plus",
        title=f"Refunded: {amount}",
        meta=_meta("Refund", amount, _day(datetime.now(UTC), tag=False)),
        lines=[f"The full {amount} for Prism Plus is on its way back to the method you paid with. Plus ended when the refund was made."],
        facts=[
            ("Refund", f"{amount} · reference {refund_id}"),
            ("Reaches you", "In 5–7 working days; a few banks take up to 10"),
            ("Plus", f"Ended on {_day(ended)}"),
        ],
        cta=("Back to the record", f"{web}/feed"),
        because="you asked for a refund of Prism Plus on {email}.",
        preheader=f"{amount} is on its way back to the method you paid with.",
    )
