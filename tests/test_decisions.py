"""The Jev client: what goes over the wire, what comes back typed, and how the
quota and transient failures map onto the stream's redelivery semantics."""

import asyncio
import json
import time

import httpx
import pytest

from common import decisions, llm
from common.decisions import Choice, ChoiceAnswer, Noul, NoulAnswer, Score, ScoreAnswer, decide

ANSWERS = {
    "model": "typesafe/jev-1.13",
    "id": "gen-1",
    "provider": "TypeSafe",
    "answers": {
        "relevant": {"type": "noul", "noul": 0.93},
        "sector": {"type": "choice", "choice": "politics", "confidence": 0.99,
                   "probabilities": {"politics": 0.99, "other": 0.01}},
        "heat": {"type": "score", "score": 1.4, "confidence": 0.7, "probabilities": {"0": 0.1, "1": 0.5, "2": 0.4}},
    },
    "usage": {"input_tokens": 1044, "output_tokens": 312, "cost": 4.3848e-05},
}

QUESTIONS = {
    "relevant": Noul(instructions="A real public event"),
    "sector": Choice(instructions="The sector", criteria={"politics": "govt", "other": "none fit"}),
    "heat": Score(instructions="How heated", criteria=["calm", "tense", "hostile"]),
}


def _client(handler):
    return httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://openrouter.ai")


@pytest.fixture(autouse=True)
def _reset(monkeypatch):
    monkeypatch.setattr(llm, "_cooldown_until", 0.0)
    monkeypatch.setattr(decisions, "_client", None)


def test_the_request_is_the_decisions_wire_contract(monkeypatch):
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers.get("authorization")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=ANSWERS)

    monkeypatch.setattr(decisions, "_client", _client(handler))
    out = asyncio.run(decide({"title": "t", "content": "c"}, QUESTIONS, trace_name="test"))

    assert seen["url"].endswith("/api/alpha/decisions")
    assert seen["auth"].startswith("Bearer ")
    body = seen["body"]
    assert body["model"] == decisions.get_settings().prism_model_decide
    assert body["state"] == {"title": "t", "content": "c"}
    assert body["questions"]["relevant"] == {"type": "noul", "instructions": "A real public event"}
    assert body["questions"]["sector"] == {
        "type": "choice", "instructions": "The sector", "criteria": {"politics": "govt", "other": "none fit"},
    }
    assert body["questions"]["heat"] == {"type": "score", "instructions": "How heated", "criteria": ["calm", "tense", "hostile"]}

    assert isinstance(out.answers["relevant"], NoulAnswer) and out.answers["relevant"].noul == 0.93
    sector = out.answers["sector"]
    assert isinstance(sector, ChoiceAnswer) and (sector.choice, sector.confidence) == ("politics", 0.99)
    assert isinstance(out.answers["heat"], ScoreAnswer) and out.answers["heat"].score == 1.4
    assert out.usage.cost == pytest.approx(4.3848e-05)


def test_an_answer_without_a_type_tag_is_still_typed_by_its_keys(monkeypatch):
    untagged = {**ANSWERS, "answers": {"relevant": {"noul": 0.2}, "sector": {"choice": "other", "confidence": 1, "probabilities": {}}}}
    monkeypatch.setattr(decisions, "_client", _client(lambda r: httpx.Response(200, json=untagged)))
    out = asyncio.run(decide({}, {k: QUESTIONS[k] for k in ("relevant", "sector")}, trace_name="test"))
    assert isinstance(out.answers["relevant"], NoulAnswer)
    assert isinstance(out.answers["sector"], ChoiceAnswer)


def test_a_402_is_a_quota_error_that_starts_the_shared_cooldown(monkeypatch):
    monkeypatch.setattr(decisions, "_client", _client(lambda r: httpx.Response(402, json={"error": {"message": "Insufficient credits"}})))
    with pytest.raises(llm.LlmQuotaError):
        asyncio.run(decide({}, QUESTIONS, trace_name="test"))
    assert llm._cooldown_until > time.monotonic(), "credits are account-wide: the LLM stages must pause too"


def test_a_5xx_is_retried_then_succeeds(monkeypatch):
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503) if len(calls) == 1 else httpx.Response(200, json=ANSWERS)

    monkeypatch.setattr(decisions, "_client", _client(handler))
    monkeypatch.setattr(decisions, "_RETRY_BACKOFF_S", 0.0)
    out = asyncio.run(decide({}, QUESTIONS, trace_name="test"))
    assert len(calls) == 2 and out.answers["relevant"].noul == 0.93


def test_a_5xx_that_never_recovers_is_transient_for_the_stream(monkeypatch):
    monkeypatch.setattr(decisions, "_client", _client(lambda r: httpx.Response(502)))
    monkeypatch.setattr(decisions, "_RETRY_BACKOFF_S", 0.0)
    with pytest.raises(ConnectionError):
        asyncio.run(decide({}, QUESTIONS, trace_name="test"))


def test_a_400_is_our_bug_and_dead_letters_once(monkeypatch):
    monkeypatch.setattr(decisions, "_client", _client(lambda r: httpx.Response(400, json={"error": {"message": "bad question"}})))
    with pytest.raises(ValueError, match="bad question"):
        asyncio.run(decide({}, QUESTIONS, trace_name="test"))


def test_a_missing_answer_is_a_contract_break_not_a_silent_default(monkeypatch):
    partial = {**ANSWERS, "answers": {"relevant": {"type": "noul", "noul": 0.5}}}
    monkeypatch.setattr(decisions, "_client", _client(lambda r: httpx.Response(200, json=partial)))
    with pytest.raises(ValueError, match="sector"):
        asyncio.run(decide({}, QUESTIONS, trace_name="test"))
