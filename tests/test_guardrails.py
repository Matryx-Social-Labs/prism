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


async def test_veto_disabled_spends_nothing(monkeypatch):
    """The veto is the most expensive scheduled pass in the product, so the switch
    has to short-circuit BEFORE the session opens — not merely skip the publish
    after the LLM calls have already been paid for."""
    monkeypatch.setenv("PRISM_VETO_ENABLED", "false")
    get_settings.cache_clear()
    import correlation.partition as partition

    def boom(*args, **kwargs):
        raise AssertionError("veto did work despite PRISM_VETO_ENABLED=false")

    monkeypatch.setattr(partition, "session_scope", boom)
    assert await partition.persist_veto_overlay() is None


async def test_veto_enabled_by_default_still_reaches_the_work(monkeypatch):
    """Counterpart: the guard must gate on the flag, not be an unconditional early
    return. Without this, deleting the `if` body's condition passes the test above."""
    monkeypatch.delenv("PRISM_VETO_ENABLED", raising=False)
    get_settings.cache_clear()
    import correlation.partition as partition

    reached = False

    def marker(*args, **kwargs):
        nonlocal reached
        reached = True
        raise RuntimeError("stop here — we only needed to know the guard let us past")

    monkeypatch.setattr(partition, "session_scope", marker)
    with pytest.raises(RuntimeError):
        await partition.persist_veto_overlay()
    assert reached is True


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


def test_the_model_column_is_not_hardcoded_to_a_provider():
    """enrichments.model is the first thing anyone reads when attributing spend,
    and its prefix is load-bearing: correlation/consumer.py and tools/scratch.py
    both test `startswith("deterministic:")` to identify CVE records.

    It was hardcoded to "ollama:" while llm_provider defaulted to openrouter and
    the OpenRouter key was set, so every row named a provider that had never been
    called — which is exactly how a spend investigation was misled on 2026-08-03.

    This reads the source rather than driving handle_classified_item, which needs
    network, an LLM and a database to reach one f-string. A source assertion is
    the proportionate guard for "someone hardcoded the provider again", and unlike
    testing the f-string in isolation it cannot pass while the caller ignores it.
    """
    import inspect

    import enrichment.consumer as mod

    src = inspect.getsource(mod)
    assert 'f"ollama:' not in src and "f'ollama:" not in src, (
        "provider hardcoded in the model tag — use settings.llm_provider"
    )
    assert "settings.llm_provider" in src, "the model tag must name the provider actually configured"
    # The deterministic prefix is NOT a provider and must survive: two call sites
    # rely on it to mark articles that no fuzzy matching may ever touch.
    assert '"deterministic:cisa_kev"' in src


def test_deterministic_prefix_is_not_a_provider():
    """The counterpart. Whatever the provider, a CVE record keeps its own prefix."""
    assert "deterministic:cisa_kev".startswith("deterministic:")
    assert not "deterministic:cisa_kev".startswith("openrouter:")
