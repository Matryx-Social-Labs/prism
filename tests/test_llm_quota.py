"""Provider billing/quota errors pause LLM calls (global cooldown) instead of
hammering the API per message. 402 (OpenRouter "insufficient credits") must be
treated like the other quota statuses so a spent account self-heals on top-up."""

import time

import httpx
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
