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
