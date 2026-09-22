"""The September audit's security batch (docs/AUDIT-2026-09.md C2, H1, H3, H5, H6,
H7, H16, H17): each fix has the one check that fails if it is undone."""

import asyncio
import re
import time

import pytest
import structlog
from fastapi import HTTPException
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api import deps
from api.deps import ADMIN_TOKEN_PLACEHOLDER, assert_admin_token_configured, require_admin
from common import auth, llm, moderation, quota
from common.config import get_settings
from common.db import session_scope
from common.imagehash import refuse_non_public
from podcasts.feeds import podcast_client

# ── C2: admin token ──────────────────────────────────────────────────────────


def test_the_placeholder_token_refuses_to_serve_off_a_laptop(monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "prism_admin_token", ADMIN_TOKEN_PLACEHOLDER)
    monkeypatch.setattr(s, "prism_web_url", "https://www.readprism.news")
    with pytest.raises(RuntimeError, match="PRISM_ADMIN_TOKEN"):
        assert_admin_token_configured(s)
    monkeypatch.setattr(s, "prism_web_url", "http://localhost:3000")
    assert_admin_token_configured(s)  # a laptop may keep the default


def test_require_admin_compares_in_constant_time_and_rejects_the_wrong_token(monkeypatch):
    monkeypatch.setattr(get_settings(), "prism_admin_token", "s3cret")
    with pytest.raises(HTTPException) as e:
        asyncio.run(require_admin("wrong"))
    assert e.value.status_code == 403
    with pytest.raises(HTTPException):
        asyncio.run(require_admin(""))
    assert asyncio.run(require_admin("s3cret")) is None
    import inspect

    assert "compare_digest" in inspect.getsource(deps.require_admin)


# ── H1: podcast fetches refuse private addresses ─────────────────────────────


def test_podcast_client_refuses_private_addresses_on_every_hop():
    client = podcast_client(5)
    assert refuse_non_public in client.event_hooks["request"]
    assert client.follow_redirects


# ── H3: CORS is this project's previews, not every tenant's ──────────────────


def test_cors_preview_regex_is_pinned_to_this_project():
    from api.main import app

    cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
    pattern = re.compile(cors.kwargs["allow_origin_regex"])
    assert pattern.fullmatch("https://prism-n77glscw2-matrixsociallabs-projects.vercel.app")
    assert not pattern.fullmatch("https://evil.vercel.app")
    assert not pattern.fullmatch("https://prism-x-someone-else.vercel.app")


# ── H5: sign-out revokes the session row ─────────────────────────────────────


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def test_a_revoked_session_no_longer_resolves():
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        user_id = await auth.user_for_verified_email(s, f"t-{time.time_ns()}@example.test")
        token = await auth.create_session(s, user_id)
    async with session_scope() as s:
        assert await auth.resolve_session(s, token) == user_id
        assert await auth.revoke_session(s, token) is True
    async with session_scope() as s:
        assert await auth.resolve_session(s, token) is None
        assert await auth.revoke_session(s, token) is False


# ── H6/H7: a limiter or guard that is down says so ───────────────────────────


def test_a_throttle_check_failure_is_logged_not_swallowed(monkeypatch):
    def broken_redis():
        raise ConnectionError("redis down")

    monkeypatch.setattr("common.stream.get_redis", broken_redis)
    with structlog.testing.capture_logs() as logs:
        assert asyncio.run(quota.ask_burst_ok("sess", "203.0.113.1", anonymous=True)) is None
    assert any(e["event"] == "ask_throttle_check_failed" and e["error_type"] == "ConnectionError" for e in logs)


def test_the_guard_escalates_to_error_after_repeated_failures(monkeypatch):
    async def down(**kw):
        raise ConnectionError("guard model down")

    monkeypatch.setattr(moderation, "structured_chat", down)
    monkeypatch.setattr(moderation, "_consecutive_failures", 0)
    with structlog.testing.capture_logs() as logs:
        for _ in range(moderation.GUARD_FAILURE_ALERT_AFTER):
            assert asyncio.run(moderation.guard_question("hi")).allowed is True
    levels = [e["log_level"] for e in logs if e["event"] == "ask_guard_failed"]
    assert levels[:-1] == ["warning"] * (moderation.GUARD_FAILURE_ALERT_AFTER - 1) and levels[-1] == "error"


# ── H16/H17: one deadline per call; a 429 pauses one model ───────────────────


def test_a_429_pauses_only_the_model_that_hit_it(monkeypatch):
    monkeypatch.setattr(llm, "_cooldown_until", 0.0)
    monkeypatch.setattr(llm, "_model_cooldown_until", {})
    llm.start_cooldown(429, "rate limited", model="judge-model")
    assert llm.model_cooldown_remaining("judge-model") > 0
    assert llm.model_cooldown_remaining("gate-model") == 0
    assert llm._cooldown_until == 0.0, "a 429 must not pause the account"
    llm.start_cooldown(402, "insufficient credits", model="judge-model")
    assert llm._cooldown_until > time.monotonic(), "a 402 is the account"


def test_a_hung_provider_costs_one_deadline_not_nine_attempts(monkeypatch):
    class Hung:
        class chat:
            class completions:
                @staticmethod
                async def create(**kw):
                    await asyncio.sleep(10)

    monkeypatch.setattr(llm, "get_llm", lambda: Hung())
    monkeypatch.setattr(llm, "LLM_DEADLINE_SECONDS", 0.05)
    monkeypatch.setattr(llm, "_respect_cooldown", lambda: asyncio.sleep(0))
    from pydantic import BaseModel

    class Out(BaseModel):
        x: int = 0

    started = time.perf_counter()
    with pytest.raises(TimeoutError):
        asyncio.run(llm.structured_chat(model="m", messages=[], output_model=Out, trace_name="t"))
    assert time.perf_counter() - started < 2


def test_sdk_retries_are_one_so_the_deadline_holds():
    from common.llm import get_llm

    assert get_llm().max_retries == 1


# ── H2: the client address is what a trusted proxy vouches for ───────────────


class _Req:
    def __init__(self, xff: str | None, socket: str | None = "10.0.0.1"):
        self.headers = {"x-forwarded-for": xff} if xff else {}
        self.client = type("C", (), {"host": socket})() if socket else None


def test_the_client_ip_is_the_hop_our_proxy_vouched_for(monkeypatch):
    from api.deps import client_ip

    monkeypatch.setattr(get_settings(), "prism_trusted_proxy_hops", 1)
    # A caller that starts the chain themselves: the spoofed entry is on the
    # left, Railway's observation on the right. The cap must key on the right.
    assert client_ip(_Req("1.2.3.4, 203.0.113.9")) == "203.0.113.9"
    assert client_ip(_Req("203.0.113.9")) == "203.0.113.9"
    assert client_ip(_Req(None)) == "10.0.0.1"
    assert client_ip(_Req("", socket=None)) is None


def test_more_proxies_step_back_further_and_zero_trusts_the_socket(monkeypatch):
    from api.deps import client_ip

    monkeypatch.setattr(get_settings(), "prism_trusted_proxy_hops", 2)
    assert client_ip(_Req("1.2.3.4, 203.0.113.9, 198.51.100.7")) == "203.0.113.9"
    # Chain shorter than the trusted depth: a direct or misconfigured call.
    assert client_ip(_Req("203.0.113.9")) == "203.0.113.9"
    monkeypatch.setattr(get_settings(), "prism_trusted_proxy_hops", 0)
    assert client_ip(_Req("1.2.3.4, 203.0.113.9")) == "10.0.0.1"


def test_a_rotating_forwarded_header_no_longer_mints_identities(monkeypatch):
    """The anonymous Ask cap is keyed on this: one spoofing script used to get
    an unlimited number of addresses and could exhaust the day's ceiling."""
    from api.deps import client_ip

    monkeypatch.setattr(get_settings(), "prism_trusted_proxy_hops", 1)
    seen = {client_ip(_Req(f"{i}.{i}.{i}.{i}, 203.0.113.9")) for i in range(1, 50)}
    assert seen == {"203.0.113.9"}
