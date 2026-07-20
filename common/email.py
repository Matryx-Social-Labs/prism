"""Pluggable email sender.

Auth (magic-link) needs to deliver a link, but the delivery provider is a
business decision that isn't made yet (no account set up). So the interface is
pluggable and defaults to a console sender that logs the link — auth works
end-to-end in dev without any provider. Swap `prism_email_provider` to a real
backend (a ~10-line adapter) once Resend/SES/Postmark is chosen.
"""

from typing import Protocol

import httpx

from common.config import get_settings
from common.logging import get_logger

logger = get_logger(__name__)


class EmailSender(Protocol):
    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class ConsoleEmailSender:
    """Dev sender: logs the message instead of delivering it. The magic link
    appears in the worker/API logs so a developer can complete the flow."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("email_console", to=to, subject=subject, body=body)


class ResendEmailSender:
    """Resend adapter (https://resend.com). Needs RESEND_API_KEY and a from-address
    on a verified domain (PRISM_EMAIL_FROM). Raises on failure so a dropped login
    email is loud, not silent."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        settings = get_settings()
        if not settings.resend_api_key:
            raise RuntimeError("prism_email_provider=resend but RESEND_API_KEY is unset")
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://api.resend.com/emails",
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.prism_email_from,
                    "to": [to],
                    "subject": subject,
                    # body is a plaintext link message; send as both so clients render it.
                    "text": body,
                    "html": f"<p>{body}</p>",
                },
            )
        if resp.status_code >= 300:
            raise RuntimeError(f"resend send failed ({resp.status_code}): {resp.text[:200]}")
        logger.info("email_sent", provider="resend", to=to, subject=subject)


def get_email_sender() -> EmailSender:
    provider = get_settings().prism_email_provider
    if provider == "console":
        return ConsoleEmailSender()
    if provider == "resend":
        return ResendEmailSender()
    raise NotImplementedError(
        f"email provider '{provider}' not wired — use 'console' (dev) or 'resend'"
    )
