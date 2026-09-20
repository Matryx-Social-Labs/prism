"""The three emails a subscription owes a reader: welcome, payment failed, cancelled.

Razorpay sends the receipt/invoice for every charge (customer_notify=1); these
are ours — what changed for them on Prism and what to do next. Same shell as
the sign-in email (common/email_templates), plain text first.
"""

from __future__ import annotations

import html as _html
from datetime import datetime
from typing import Any

from sqlalchemy import text

from common.config import get_settings
from common.email import get_email_sender
from common.email_templates import shell

PLAN_LABEL = {"plus_monthly": "Plus · monthly", "plus_yearly": "Plus · yearly", "founding": "Founding member"}


def _when(ts: Any) -> str | None:
    if not ts:
        return None
    from datetime import UTC

    d = datetime.fromtimestamp(int(ts), tz=UTC)
    return d.strftime("%-d %B %Y")


async def notify_transition(db, user_id: str, before: str, after: str, sub: dict[str, Any]) -> None:
    email = (await db.execute(text("SELECT email FROM users WHERE id = :u"), {"u": user_id})).scalar_one_or_none()
    if not email:
        return
    web = get_settings().prism_web_url.rstrip("/")
    plan = PLAN_LABEL.get((sub.get("notes") or {}).get("plan") or "", "Plus")
    renews = _when(sub.get("current_end"))
    if after == "active" and before in ("", "created", "past_due", "halted"):
        subject = "You're on Prism Plus"
        lines = [
            f"Thank you. Your {plan} is on.",
            "A hundred questions a day, the stronger model, answers from the whole story.",
            f"Next charge: {renews}." if renews and sub.get("status") == "active" else (f"Paid through {renews}." if renews else ""),
            "Razorpay has emailed your receipt. Cancel any time from your account — access runs to the end of the period you paid for.",
        ]
        cta = ("Your account", f"{web}/account")
    elif after == "past_due":
        subject = "A Prism Plus charge did not go through"
        lines = [
            f"The latest charge for your {plan} failed.",
            "Plus stays on for three days while it is retried. Razorpay has emailed you a link to update the payment method.",
            "If nothing changes, Plus pauses after that and your reading stays free as always.",
        ]
        cta = ("Your account", f"{web}/account")
    elif after in ("cancelled", "halted") and before in ("active", "past_due"):
        subject = "Your Prism Plus has been cancelled" if after == "cancelled" else "Prism Plus is paused"
        lines = [
            f"Your {plan} will not renew." if after == "cancelled" else f"Your {plan} is paused after repeated failed charges.",
            f"You keep Plus until {renews}." if renews and after == "cancelled" else "",
            "The record stays free for everyone. Come back to Plus any time.",
        ]
        cta = ("Plus", f"{web}/plus")
    else:
        return
    body = "\n\n".join(line for line in lines if line)
    text_body = f"{subject}\n\n{body}\n\n{cta[0]}: {cta[1]}\n\nPrism — One story. Every perspective."
    html = shell(
        title=subject,
        paragraphs=[_html.escape(line) for line in lines if line],
        cta_label=cta[0],
        cta_href=cta[1],
        footer=f"Sent to {_html.escape(email)} about your Prism subscription.",
    )
    await get_email_sender().send(to=email, subject=subject, body=text_body, html=html)
