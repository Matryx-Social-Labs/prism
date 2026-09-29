"""Tell the founders, by email, when the pipeline stops doing its job.

Collection stopped for 37 hours from 2026-09-28 02:11 UTC because the LLM
balance fell under its floor. It was logged every five minutes, and /healthz
stayed green, so nobody knew until readers saw day-old news. A condition worth
stopping the pipeline for is worth an email to PRISM_ADMIN_EMAILS — at most
once per window per condition, so a stuck state never floods the inbox.
"""

from common.config import get_settings
from common.email import get_email_sender
from common.logging import get_logger
from common.stream import get_redis

logger = get_logger(__name__)

EVERY_HOURS = 12


async def notify(key: str, subject: str, body: str, *, every_hours: int = EVERY_HOURS) -> bool:
    """Email every founder unless this `key` was sent inside the window. True
    when sent. Never raises: an alert that cannot go out is logged, and the
    caller's work goes on."""
    admins = [e.strip() for e in get_settings().prism_admin_emails.split(",") if e.strip()]
    if not admins:
        logger.warning("alert_no_recipients", key=key, subject=subject)
        return False
    try:
        if not await get_redis().set(f"alert:{key}", "1", nx=True, ex=every_hours * 3600):
            return False
    except Exception as exc:  # noqa: BLE001 — without the throttle, do not risk a flood
        logger.warning("alert_throttle_unavailable", key=key, error=str(exc)[:160])
        return False
    sender = get_email_sender()
    sent = False
    for to in admins:
        try:
            await sender.send(to=to, subject=f"[Prism] {subject}", body=body)
            sent = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("alert_send_failed", key=key, to=to, error=str(exc)[:160])
    logger.warning("alert_sent" if sent else "alert_undelivered", key=key, subject=subject)
    return sent
