"""Provider billing/quota errors pause LLM calls (global cooldown) instead of
hammering the API per message. 402 (OpenRouter "insufficient credits") must be
treated like the other quota statuses so a spent account self-heals on top-up."""

import time

import httpx
import pytest
from openai import APIStatusError

from common import llm


def _status_error(code: int) -> APIStatusError:
    resp = httpx.Response(code, request=httpx.Request("POST", "http://x"))
    return APIStatusError("boom", response=resp, body=None)


def test_402_starts_cooldown():
    llm._cooldown_until = 0.0
    llm._maybe_start_cooldown(_status_error(402))
    assert llm._cooldown_until > time.monotonic()


def test_all_quota_statuses_start_cooldown():
    for code in (401, 402, 403, 429):
        llm._cooldown_until = 0.0
        llm._maybe_start_cooldown(_status_error(code))
        assert llm._cooldown_until > time.monotonic(), code


def test_non_quota_error_no_cooldown():
    llm._cooldown_until = 0.0
    llm._maybe_start_cooldown(_status_error(500))
    assert llm._cooldown_until == 0.0


# --- a hung call must not hold an enrichment slot for ten minutes --------------


def test_the_llm_client_has_an_explicit_timeout():
    """The OpenAI client default is 600s and nothing overrode it.

    Enrichment runs 12 concurrent handlers over a stream batch of 12, so one
    hung call holds a slot for the whole default and a few of them stall the
    batch. Measured on a cold start 2026-09-03: the gate approved ~6,000
    items/hour while enrichment consumed ~180 — a 33x gap that grew the queue
    ~5,800/hour and never drained.
    """
    from common.llm import LLM_TIMEOUT_SECONDS, get_llm

    client = get_llm()
    assert client.timeout == LLM_TIMEOUT_SECONDS
    assert LLM_TIMEOUT_SECONDS < 120, (
        "a timeout at or above the batch stall defeats the purpose — it must be "
        "well under the time a slow call can hold a concurrency slot"
    )
    assert LLM_TIMEOUT_SECONDS > 30, (
        "too tight and normal extracts start failing, which turns a throughput "
        "problem into a data-loss one"
    )


def test_a_timed_out_call_is_retried_not_dropped():
    """The message stays pending on the stream and is redelivered, so a timeout
    costs latency rather than an article."""
    from common.llm import get_llm

    assert get_llm().max_retries >= 1


# --- a 403 that refuses one request is that article's, not the account's -------

GUARDRAIL = ("Error code: 403 - {'error': {'message': 'Request blocked: prompt injection patterns detected', "
             "'code': 403, 'metadata': {'patterns': ['system_override']}}}")


def _refused(message: str = GUARDRAIL) -> APIStatusError:
    resp = httpx.Response(403, request=httpx.Request("POST", "http://x"))
    return APIStatusError(message, response=resp, body=None)


def test_a_guardrail_403_pauses_nothing():
    """2026-10-01: an HT headline quoting a judge — "How does your system
    override law?" — tripped OpenRouter's prompt-injection guardrail. Read as
    quota, every redelivery paused every model call for 120 s."""
    llm._cooldown_until = 0.0
    llm._maybe_start_cooldown(_refused())
    assert llm._cooldown_until == 0.0


async def test_a_refused_article_dead_letters_after_the_fallback_is_refused_too(monkeypatch):
    from pydantic import BaseModel

    from common.config import get_settings

    class Out(BaseModel):
        ok: bool

    models = []

    class _Completions:
        async def create(self, **kw):
            models.append(kw["model"])
            raise _refused()

    class _Client:
        chat = type("Chat", (), {"completions": _Completions()})()

    async def _noop(*_a):
        return None

    monkeypatch.setattr(llm, "get_llm", lambda: _Client())
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setattr(get_settings(), "prism_model_fallback", "fallback/model")
    llm._cooldown_until = 0.0
    with pytest.raises(llm.LlmContentBlocked):  # a ValueError: the stream dead-letters it once
        await llm.structured_chat(model="m", messages=[{"role": "user", "content": "x"}], output_model=Out, trace_name="t")
    assert models == ["m", "fallback/model"]
    assert llm._cooldown_until == 0.0
