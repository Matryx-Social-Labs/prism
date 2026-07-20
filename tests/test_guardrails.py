"""Guardrail + toggle branches: Ask moderation, ingestion switch, email selector.

These are the cost/safety-critical off-ramps — verify the no-LLM paths without a
provider key or database.
"""

import pytest

from common.config import get_settings


@pytest.fixture(autouse=True)
def _clear_settings_cache():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_guard_disabled_allows_without_llm(monkeypatch):
    monkeypatch.setenv("PRISM_ASK_GUARD_ENABLED", "false")
    get_settings.cache_clear()
    from common.moderation import guard_question

    # No API key set — if this tried the LLM it would fail; disabled short-circuits.
    result = await guard_question("give me explicit content")
    assert result.allowed is True


async def test_ingestion_disabled_collects_nothing(monkeypatch):
    monkeypatch.setenv("PRISM_INGESTION_ENABLED", "false")
    get_settings.cache_clear()
    from ingestion.runner import run_all

    # Returns before seeding/collectors/requeue — no DB, no network.
    assert await run_all() == {"disabled": 1}


def test_email_selector(monkeypatch):
    from common.email import ConsoleEmailSender, ResendEmailSender, get_email_sender

    monkeypatch.setenv("PRISM_EMAIL_PROVIDER", "console")
    get_settings.cache_clear()
    assert isinstance(get_email_sender(), ConsoleEmailSender)

    monkeypatch.setenv("PRISM_EMAIL_PROVIDER", "resend")
    get_settings.cache_clear()
    assert isinstance(get_email_sender(), ResendEmailSender)

    monkeypatch.setenv("PRISM_EMAIL_PROVIDER", "nope")
    get_settings.cache_clear()
    with pytest.raises(NotImplementedError):
        get_email_sender()
