"""structured_chat's reasoning control reaches the provider, and a model that
insists on reasoning gets the smallest effort rather than losing the article."""

import pytest
from openai import APIStatusError

from common import llm


class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


@pytest.mark.asyncio
async def test_reasoning_off_is_sent_and_mandatory_reasoning_falls_back_to_minimal(monkeypatch):
    from pydantic import BaseModel

    class Out(BaseModel):
        ok: bool

    calls = []

    class _Completions:
        async def create(self, **kw):
            calls.append(kw.get("extra_body"))
            if len(calls) == 1:
                import httpx

                resp = httpx.Response(400, request=httpx.Request("POST", "https://x"), text="Reasoning is mandatory for this model")
                raise APIStatusError("Reasoning is mandatory for this model", response=resp, body=None)
            return _Resp('{"ok": true}')

    class _Client:
        chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr(llm, "get_llm", lambda: _Client())
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    from common.config import get_settings

    get_settings.cache_clear()
    out = await llm.structured_chat(model="m", messages=[{"role": "user", "content": "x"}], output_model=Out, trace_name="t", reasoning=llm.REASONING_OFF)
    assert out.ok is True
    assert calls == [{"reasoning": {"enabled": False}}, {"reasoning": {"effort": "minimal"}}]


@pytest.mark.asyncio
async def test_known_mandatory_reasoning_model_starts_at_minimal(monkeypatch):
    from pydantic import BaseModel

    class Out(BaseModel):
        ok: bool

    calls = []

    class _Completions:
        async def create(self, **kw):
            calls.append(kw.get("extra_body"))
            return _Resp('{"ok": true}')

    class _Client:
        chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr(llm, "get_llm", lambda: _Client())
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    from common.config import get_settings

    get_settings.cache_clear()
    out = await llm.structured_chat(
        model="google/gemini-3.5-flash",
        messages=[{"role": "user", "content": "x"}],
        output_model=Out,
        trace_name="t",
        reasoning=llm.REASONING_OFF,
    )
    assert out.ok is True
    assert calls == [{"reasoning": {"effort": "minimal"}}]


async def _noop():
    return None


@pytest.mark.asyncio
async def test_an_empty_provider_answer_is_transient_not_a_parse_failure(monkeypatch):
    """finish_reason 'error' with null content: retried once, then raised as a
    ConnectionError so the stream keeps the message instead of dropping it."""
    from pydantic import BaseModel

    class Out(BaseModel):
        ok: bool

    class _Completions:
        async def create(self, **kw):
            r = _Resp(None)
            r.choices[0].finish_reason = "error"
            return r

    class _Client:
        chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr(llm, "get_llm", lambda: _Client())
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setattr(llm.asyncio, "sleep", _sleep0)
    with pytest.raises(llm.LlmEmptyResponse):
        await llm.structured_chat(model="m", messages=[{"role": "user", "content": "x"}], output_model=Out, trace_name="t")


@pytest.mark.asyncio
async def test_a_provider_answer_without_choices_is_transient(monkeypatch):
    from pydantic import BaseModel

    class Out(BaseModel):
        ok: bool

    class _Completions:
        async def create(self, **kw):
            return type("Response", (), {"choices": None})()

    class _Client:
        chat = type("Chat", (), {"completions": _Completions()})()

    monkeypatch.setattr(llm, "get_llm", lambda: _Client())
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    monkeypatch.setattr(llm.asyncio, "sleep", _sleep0)
    with pytest.raises(llm.LlmEmptyResponse):
        await llm.structured_chat(
            model="m",
            messages=[{"role": "user", "content": "x"}],
            output_model=Out,
            trace_name="t",
        )


async def _sleep0(_):
    return None
