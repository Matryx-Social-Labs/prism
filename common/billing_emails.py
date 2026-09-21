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

import html as _html
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text

from common.config import get_settings
from common.email import get_email_sender
from common.email_templates import PROMISE, shell

PLAN_LABEL = {"plus_monthly": "Plus · monthly", "plus_yearly": "Plus · yearly", "founding": "Founding member"}

# Razorpay charges, invoices and retries on IST — a cycle ends at 00:00 IST —
# so every date about money is the Indian calendar day, tagged IST, the same
# words the receipt uses (a reader in Berlin who paid at 20:50 on the 20th was
# charged on the 21st and is billed again on the 21st; the UTC date said the
# 20th, 2026-09-21). The date in the meta line is today's, untagged.
IST = ZoneInfo("Asia/Kolkata")


def _day(d: datetime | None, *, tag: bool = True) -> str | None:
    if not d:
        return None
    s = d.astimezone(IST).strftime("%-d %B %Y")
    return f"{s} IST" if tag else s


def _ts(ts: Any) -> datetime | None:
    return datetime.fromtimestamp(int(ts), tz=UTC) if ts else None


def rupees(paise: int | None) -> str | None:
    return f"₹{paise // 100:,}" if paise else None


async def _send(
    db,
    user_id: str,
    *,
    subject: str,
    meta: str,
    lines: list[str],
    facts: list[tuple[str, str]],
    cta: tuple[str, str] | None,
    preheader: str | None = None,
) -> None:
    email = (await db.execute(text("SELECT email FROM users WHERE id = :u"), {"u": user_id})).scalar_one_or_none()
    if not email:
        return
    lines = [x for x in lines if x]
    facts = [(k, v) for k, v in facts if v]
    text_body = f"{subject}\n\n" + "\n\n".join(lines)
    if facts:
        text_body += "\n\n" + "\n".join(f"{k}: {v}" for k, v in facts)
    if cta:
        text_body += f"\n\n{cta[0]}: {cta[1]}"
    text_body += f"\n\nPrism — {PROMISE}"
    html = shell(
        title=subject,
        meta=meta,
        paragraphs=[_html.escape(x) for x in lines],
        facts=[(k, _html.escape(v)) for k, v in facts],
        cta=cta,
        footer=f"Sent to {_html.escape(email)} about your Prism subscription.",
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
    today = _day(datetime.now(UTC), tag=False)
    meta = " · ".join(x for x in (plan, price, today) if x)

    if after == "active" and before == "paused":
        await _send(
            db,
            user_id,
            subject="Prism Plus is back on",
            meta=meta,
            lines=[f"Your {plan} has resumed. A hundred questions a day, the stronger model, the whole story."],
            facts=[("Plan", " · ".join(x for x in (plan, price) if x)), ("Next charge", _day(_ts(sub.get("charge_at"))) or _day(end) or "")],
            cta=("Back to the record", f"{web}/feed"),
            preheader="Welcome back. Plus has resumed.",
        )
        return

    if after == "paused":
        return  # the route that paused it has already written

    starts = _ts(sub.get("start_at"))
    if after == "active" and before in ("", "created") and starts and not sub.get("current_start") and starts > datetime.now(UTC):
        await _send(
            db,
            user_id,
            subject="Your yearly Plus is set",
            meta=meta,
            lines=[
                f"Done — your {plan} begins on {_day(starts)}, the day your current month ends. Nothing changes until then, and nothing is charged twice.",
                "Razorpay has confirmed the mandate; the first yearly charge is made on that day.",
            ],
            facts=[("Plan", " · ".join(x for x in (plan, price) if x)), ("Starts", _day(starts) or ""), ("First charge", _day(starts) or "")],
            cta=("Your account", f"{web}/account"),
            preheader=f"Your yearly Plus starts {_day(starts)}.",
        )
        return

    if after == "active" and before in ("", "created", "past_due", "halted"):
        renews = _day(end) if sub.get("status") == "active" else None
        await _send(
            db,
            user_id,
            subject="You're on Prism Plus",
            meta=meta,
            lines=[
                f"Thank you. Your {plan} is on.",
                "A hundred questions a day, the stronger model, answers drawn from the whole story rather than one report.",
            ],
            facts=[
                ("Plan", " · ".join(x for x in (plan, price) if x)),
                ("Next charge", renews or "") if renews else ("Paid through", _day(end) or ""),
                ("Receipt", "Razorpay has emailed it to this address"),
                ("Changing your mind", "Cancel any time from your account; access runs to the end of the period you paid for"),
            ],
            cta=("Your account", f"{web}/account"),
            preheader=f"Your {plan} is on. Ask more of every story.",
        )
        return

    if after == "past_due":
        await _send(
            db,
            user_id,
            subject="A Prism Plus charge did not go through",
            meta=meta,
            lines=[
                f"The latest charge for your {plan} failed.",
                "Plus stays on for three days while Razorpay retries. Razorpay has emailed you a link to update the payment method.",
                "If nothing changes, Plus pauses after that and your reading stays free as always.",
            ],
            facts=[("Plan", " · ".join(x for x in (plan, price) if x)), ("Plus stays on until", _day(end) or "")],
            cta=("Your account", f"{web}/account"),
            preheader="Plus stays on for three days while the charge is retried.",
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
        still_on = end is not None and end > datetime.now(UTC)
        if after == "halted":
            subject, lines = "Prism Plus is paused", [
                f"Your {plan} is paused after repeated failed charges.",
                "The record stays free for everyone. Come back to Plus any time.",
            ]
        elif still_on and not scheduled:
            subject, lines = "Your Prism Plus will not renew", [
                f"Your {plan} has been cancelled and will not be charged again.",
                f"You keep Plus until {_day(end)}.",
                "The record stays free for everyone. Come back to Plus any time.",
            ]
        else:
            subject, lines = "Your Prism Plus has ended", [
                f"Your {plan} ended{' on ' + _day(end) if end else ''}. No further charges.",
                "Every record, source, quote and clip stays open to you; the free plan keeps ten questions a day.",
                "Come back to Plus any time.",
            ]
        await _send(db, user_id, subject=subject, meta=meta, lines=lines, facts=[], cta=("Plus", f"{web}/plus"), preheader=lines[0])


async def notify_cancel_scheduled(db, user_id: str, *, plan_key: str, price_paise: int | None, access_until: datetime | None) -> None:
    """The reader clicked Cancel: say at once what happens and when."""
    web = get_settings().prism_web_url.rstrip("/")
    plan = PLAN_LABEL.get(plan_key, "Plus")
    until = _day(access_until)
    await _send(
        db,
        user_id,
        subject="Your Prism Plus is set to end",
        meta=" · ".join(x for x in (plan, rupees(price_paise), _day(datetime.now(UTC), tag=False)) if x),
        lines=[
            f"Done — your {plan} will not renew, and nothing more will be charged.",
            f"You keep Plus until {until}." if until else "You keep Plus to the end of the period you paid for.",
            "Changed your mind? Subscribe again from the Plus page whenever you like.",
        ],
        facts=[("Plus ends", until or ""), ("Further charges", "None")],
        cta=("Your account", f"{web}/account"),
        preheader=f"No further charges. Plus stays on until {until}." if until else "No further charges.",
    )


async def notify_paused(db, user_id: str, *, plan_key: str, price_paise: int | None, paid_until: datetime | None, resumes: datetime) -> None:
    """The reader paused instead of cancelling: what stays, what stops, when it returns."""
    web = get_settings().prism_web_url.rstrip("/")
    plan = PLAN_LABEL.get(plan_key, "Plus")
    await _send(
        db,
        user_id,
        subject="Prism Plus is paused",
        meta=" · ".join(x for x in (plan, rupees(price_paise), _day(datetime.now(UTC), tag=False)) if x),
        lines=[
            f"Your {plan} is paused. You keep Plus to the end of the month you paid for; after that nothing is charged until {_day(resumes)}, when it comes back on its own.",
            "Want it back sooner? Resume from your account any time.",
        ],
        facts=[("Plus stays on until", _day(paid_until) or ""), ("Charges", "None while paused"), ("Resumes", _day(resumes) or "")],
        cta=("Your account", f"{web}/account"),
        preheader=f"No charges until {_day(resumes)}. Resume sooner any time.",
    )


async def notify_refund(db, user_id: str, *, plan_key: str, amount_paise: int, refund_id: str, ended: datetime) -> None:
    """The 7-day refund went through: the amount, where it goes, and when."""
    web = get_settings().prism_web_url.rstrip("/")
    plan = PLAN_LABEL.get(plan_key, "Plus")
    amount = rupees(amount_paise) or ""
    await _send(
        db,
        user_id,
        subject=f"Refunded: {amount} for Prism Plus",
        meta=" · ".join(x for x in (plan, amount, _day(datetime.now(UTC), tag=False)) if x),
        lines=[
            f"Your {plan} charge of {amount} has been refunded in full, and Plus ended today.",
            "Razorpay returns it to the card, bank account or UPI app you paid with. Most banks show it within 5–7 working days; a few take up to 10.",
            "Reading stays free. Thank you for trying Plus.",
        ],
        facts=[
            ("Refund", f"{amount} · Razorpay ref {refund_id}"),
            ("Reaches you", "5–7 working days, to the method you paid with"),
            ("Plus ended", _day(ended) or ""),
        ],
        cta=("Back to the record", f"{web}/feed"),
        preheader=f"{amount} is on its way back to the method you paid with.",
    )
