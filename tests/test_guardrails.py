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


# --- Langfuse kill switch ----------------------------------------------------
# The self-hosted stack cost $70 in two weeks and now scales to zero after 10 idle
# minutes, so ONE background span wakes web + worker + ClickHouse + MinIO and
# restarts billing. These verify the switch short-circuits before the SDK is
# touched at all — not that it merely drops the span after paying for it.


def test_tracing_is_off_by_default_even_with_credentials(monkeypatch):
    """Credentials present must NOT be the same thing as "please start billing".
    That was the old rule and it made cost a side effect of configuration."""
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    monkeypatch.delenv("PRISM_LANGFUSE_ENABLED", raising=False)
    get_settings.cache_clear()
    assert get_settings().langfuse_enabled is False


def test_the_switch_needs_credentials_too(monkeypatch):
    monkeypatch.setenv("PRISM_LANGFUSE_ENABLED", "true")
    # Empty, not deleted: Settings also reads .env, so delenv would leave the real
    # local credentials in place and the assertion would pass for the wrong reason.
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    get_settings.cache_clear()
    assert get_settings().langfuse_enabled is False


def test_both_together_enable_it(monkeypatch):
    """The counterpart: the guard must gate on the flag, not be an unconditional
    'off'. Without this, hardcoding False passes every test above."""
    monkeypatch.setenv("PRISM_LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    get_settings.cache_clear()
    assert get_settings().langfuse_enabled is True


async def test_disabled_observe_never_touches_the_sdk(monkeypatch):
    """The cost-critical assertion. If the SDK decorator is reached at all, a
    client is constructed and an exporter thread starts — which wakes the stack."""
    monkeypatch.delenv("PRISM_LANGFUSE_ENABLED", raising=False)
    get_settings.cache_clear()
    import common.observability as obs

    def boom(*args, **kwargs):
        raise AssertionError("Langfuse SDK was reached despite tracing being disabled")

    monkeypatch.setattr(obs, "_sdk_observe", boom)
    monkeypatch.setattr(obs, "get_client", boom)

    @obs.observe(name="test-stage")
    async def stage(x):
        return x * 2

    assert await stage(21) == 42  # and the stage itself still works


def test_disabled_get_langfuse_returns_none_without_a_client(monkeypatch):
    monkeypatch.delenv("PRISM_LANGFUSE_ENABLED", raising=False)
    get_settings.cache_clear()
    import common.observability as obs

    def boom(*args, **kwargs):
        raise AssertionError("client constructed despite tracing being disabled")

    monkeypatch.setattr(obs, "get_client", boom)
    assert obs.get_langfuse() is None


async def test_enabled_observe_does_reach_the_sdk(monkeypatch):
    """Counterpart again — otherwise 'never call the SDK' passes by doing nothing."""
    monkeypatch.setenv("PRISM_LANGFUSE_ENABLED", "true")
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "pk-lf-test")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "sk-lf-test")
    get_settings.cache_clear()
    import common.observability as obs

    reached = {"n": 0}

    def fake_observe(*dargs, **dkwargs):
        def deco(fn):
            reached["n"] += 1
            return fn
        return deco

    monkeypatch.setattr(obs, "_sdk_observe", fake_observe)

    @obs.observe(name="test-stage")
    async def stage(x):
        return x + 1

    assert await stage(1) == 2
    assert reached["n"] == 1, "the SDK decorator was not applied when tracing is on"


def test_prompts_still_work_with_tracing_off(monkeypatch):
    """Prompt fetching must fall back locally, not fail — otherwise turning off
    tracing would take the pipeline down with it."""
    monkeypatch.delenv("PRISM_LANGFUSE_ENABLED", raising=False)
    get_settings.cache_clear()
    from common.observability import fetch_prompt

    prompt = fetch_prompt("extract-shared")
    assert prompt.version == 0 and prompt.compile(title="t", source="s", published_at="p", text="x")


def test_settings_repr_does_not_leak_credentials():
    """pytest prints the whole Settings object on any assertion failure involving
    it, and CI keeps those logs. A real NVD key and the production database URL
    (with password) were visible in a local failure while writing these tests."""
    monkey = get_settings()
    text = repr(monkey)
    for field in ("nvd_api_key", "openrouter_api_key", "langfuse_secret_key",
                  "prism_admin_token", "database_url", "redis_url", "resend_api_key"):
        assert field not in text, f"{field} appears in Settings repr — it will reach CI logs"
    # Non-secret config must still be visible, or debugging becomes guesswork.
    assert "prism_langfuse_enabled" in text
