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


async def _noop():
    return None
