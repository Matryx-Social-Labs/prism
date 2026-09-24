"""A reader's own words go only to providers that neither retain nor train on them.

The privacy policy names OpenRouter and its routed providers as receiving Ask
questions; OpenRouter's default routing includes providers that may keep them.
Pinned: every call carrying reader text (the Ask answer, the guard that reads the
question) sends `provider.data_collection: "deny"`, the retry paths that rebuild
the request keep it, and pipeline calls over published news do not send it.
"""

import uuid

import httpx
import pytest
from openai import APIStatusError
from pydantic import BaseModel

from common import llm

pytestmark = pytest.mark.asyncio(loop_scope="session")

DENY = {"data_collection": "deny"}


class Out(BaseModel):
    ok: bool


class _Resp:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})()]


def _client(calls, fail_first_with=None):
    class _Completions:
        async def create(self, **kw):
            calls.append(kw.get("extra_body"))
            if fail_first_with and len(calls) == 1:
                resp = httpx.Response(400, request=httpx.Request("POST", "https://x"), text=fail_first_with)
                raise APIStatusError(fail_first_with, response=resp, body=None)
            return _Resp('{"ok": true}')

    return type("Client", (), {"chat": type("Chat", (), {"completions": _Completions()})()})()


async def _noop(*_a, **_kw):
    return None


@pytest.fixture(autouse=True)
def _openrouter(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setattr(llm, "_respect_cooldown", _noop)
    from common.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def test_private_calls_refuse_data_collection_and_keep_it_through_the_reasoning_retry(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "get_llm", lambda: _client(calls, fail_first_with="Reasoning is mandatory for this model"))
    out = await llm.structured_chat(model="m", messages=[{"role": "user", "content": "x"}], output_model=Out,
                                    trace_name="t", reasoning=llm.REASONING_OFF, private=True)
    assert out.ok
    assert calls == [
        {"reasoning": {"enabled": False}, "provider": DENY},
        {"reasoning": {"effort": "minimal"}, "provider": DENY},
    ]


async def test_the_content_fallback_keeps_the_provider_rule():
    kwargs = {"model": "m", "extra_body": {"reasoning": {"enabled": False}, "provider": DENY}}
    from common.config import get_settings

    get_settings().prism_model_fallback = "fallback/model"
    assert llm._swap_to_fallback(kwargs, llm.REASONING_OFF, "t")
    assert kwargs["model"] == "fallback/model"
    assert kwargs["extra_body"]["provider"] == DENY


async def test_pipeline_calls_over_published_news_do_not_send_it(monkeypatch):
    calls = []
    monkeypatch.setattr(llm, "get_llm", lambda: _client(calls))
    await llm.structured_chat(model="m", messages=[{"role": "user", "content": "x"}], output_model=Out,
                              trace_name="t", reasoning=llm.REASONING_OFF)
    assert calls == [{"reasoning": {"enabled": False}}]


async def test_the_guard_reading_the_question_is_private(monkeypatch):
    from common import moderation

    seen = {}

    async def _capture(**kw):
        seen.update(kw)
        return moderation.GuardResult(allowed=True, category="ok")

    monkeypatch.setattr(moderation, "structured_chat", _capture)
    monkeypatch.setattr(moderation.get_settings(), "prism_ask_guard_enabled", True)
    await moderation.guard_question("what did the minister say?")
    assert seen.get("private") is True


async def test_the_ask_answer_is_private(monkeypatch):
    import agent.rag as rag
    from tests.test_rag import _allow, _grounded, _Prompt, _Streaming, chunk

    sent = {}
    streaming = _Streaming("Answer [1].")
    real_create = streaming.chat.completions.create

    async def _create(**kw):
        sent.update(kw)
        return await real_create(**kw)

    streaming.chat.completions.create = _create
    monkeypatch.setattr(rag, "guard_question", _allow())
    monkeypatch.setattr(rag, "retrieve_grounding", lambda _e, _q, **_kw: _grounded([chunk(1)]))
    monkeypatch.setattr(rag, "get_llm", lambda: streaming)
    monkeypatch.setattr(rag, "fetch_prompt", lambda _n: _Prompt())
    monkeypatch.setattr(rag, "_persist_turn", _noop)
    events = [e async for e in rag.answer_stream(event_id=uuid.uuid4(), session_id=uuid.uuid4(), question="q")]
    assert any(e["type"] == "done" for e in events)
    assert sent["extra_body"]["provider"] == DENY
