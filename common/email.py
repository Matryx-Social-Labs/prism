"""Pluggable email sender.

Auth (magic-link) needs to deliver a link, but the delivery provider is a
business decision that isn't made yet (no account set up). So the interface is
pluggable and defaults to a console sender that logs the link — auth works
end-to-end in dev without any provider. Swap `prism_email_provider` to a real
backend (a ~10-line adapter) once Resend/SES/Postmark is chosen.
"""

from typing import Protocol

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


def get_email_sender() -> EmailSender:
    provider = get_settings().prism_email_provider
    if provider == "console":
        return ConsoleEmailSender()
    # Real providers plug in here — each is a small adapter implementing
    # EmailSender.send (Resend/SES/Postmark). Failing loud beats silently
    # dropping a login email.
    raise NotImplementedError(
        f"email provider '{provider}' not wired yet — set prism_email_provider=console "
        "for dev, or add the adapter in common/email.py"
    )
