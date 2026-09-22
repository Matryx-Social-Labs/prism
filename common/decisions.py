"""Typed decisions — TypeSafe Jev through OpenRouter's Decisions API.

Jev is not a chat model. It reads a STATE (any JSON — for us a title and a
body) and answers a set of QUESTIONS in one parallel pass, each answer typed
with a probability: a `noul` is a yes/no probability, a `choice` picks one of
up to 255 named options with a confidence and the full distribution, a
`score` places the state on an ordered rubric. It never writes text, so it
cannot invent a field or a sector; what it cannot do is generate — a headline,
a rationale, an entity list stay with the chat models.

Wire contract (alpha, measured 2026-09-22): POST {openrouter}/api/alpha/decisions
with {model, state, questions}; back comes {answers, usage: {input_tokens,
output_tokens, cost}, model, id, provider}. $0.042 per million input tokens,
output free; 64k tokens of state + questions per call; 1,200 requests a minute.
Same API key as the chat client, same attribution headers, same quota
cooldown: the credits are one account.

Failure semantics follow common/llm.py so the stream consumers need no new
branch: quota (402/429/401/403) is LlmQuotaError and pauses every model call;
a 5xx or a timeout is retried twice and then a ConnectionError (the message
stays pending and is redelivered); any other 4xx is a ValueError (our request
is wrong; dead-letter once, do not redeliver).
"""

from __future__ import annotations

import asyncio
import time
from typing import Annotated, Any, Literal

import httpx
from pydantic import BaseModel, Field, TypeAdapter

from common.config import get_settings
from common.llm import QUOTA_STATUS, LlmQuotaError, respect_cooldown, start_cooldown
from common.logging import get_logger
from common.observability import get_langfuse, observe

logger = get_logger(__name__)

DECISIONS_TIMEOUT_S = 15.0
_RETRIES = 2
_RETRY_BACKOFF_S = 0.5
_client: httpx.AsyncClient | None = None


# ── Questions ────────────────────────────────────────────────────────────────


class Noul(BaseModel):
    """A yes/no question, answered as a probability that the statement holds."""

    type: Literal["noul"] = "noul"
    instructions: str


class Choice(BaseModel):
    """Pick one option; criteria maps each option key to what it means."""

    type: Literal["choice"] = "choice"
    instructions: str
    criteria: dict[str, str]


class Score(BaseModel):
    """A position on an ordered rubric; criteria lists the levels, low to high."""

    type: Literal["score"] = "score"
    instructions: str
    criteria: list[str]


Question = Noul | Choice | Score


# ── Answers ──────────────────────────────────────────────────────────────────


class NoulAnswer(BaseModel):
    type: Literal["noul"] = "noul"
    noul: float = Field(ge=0.0, le=1.0)


class ChoiceAnswer(BaseModel):
    type: Literal["choice"] = "choice"
    choice: str
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float] = Field(default_factory=dict)


class ScoreAnswer(BaseModel):
    type: Literal["score"] = "score"
    score: float
    confidence: float = Field(ge=0.0, le=1.0)
    probabilities: dict[str, float] = Field(default_factory=dict)


Answer = Annotated[NoulAnswer | ChoiceAnswer | ScoreAnswer, Field(discriminator="type")]
_ANSWER = TypeAdapter(Answer)


class Usage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0
    cost: float = 0.0


class Decisions(BaseModel):
    answers: dict[str, Answer]
    usage: Usage = Field(default_factory=Usage)
    model: str = ""
    id: str = ""


def _typed(raw: dict[str, Any]) -> dict[str, Any]:
    """The alpha endpoint tags answers with their type; tolerate its absence by
    reading the type off the answer's own key, so a contract drift shows up as
    a validation error on the field, not as a silently untyped answer."""
    if "type" not in raw:
        for key in ("choice", "score", "noul"):
            if key in raw:
                return {"type": key, **raw}
    return raw


# ── Client ───────────────────────────────────────────────────────────────────


def _decisions_url() -> str:
    # The chat base is .../api/v1; the decisions endpoint lives beside it.
    return get_settings().openrouter_base_url.rsplit("/v1", 1)[0] + "/alpha/decisions"


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=DECISIONS_TIMEOUT_S)
    return _client


def _headers() -> dict[str, str]:
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.openrouter_api_key or 'missing-openrouter-key'}",
        "HTTP-Referer": settings.prism_web_url,
        "X-Title": "Prism",
    }


@observe(as_type="generation")
async def decide(
    state: dict[str, Any],
    questions: dict[str, Question],
    *,
    trace_name: str,
    metadata: dict[str, Any] | None = None,
) -> Decisions:
    """One Decisions call: every question answered from the same state."""
    settings = get_settings()
    body = {
        "model": settings.prism_model_decide,
        "state": state,
        "questions": {k: q.model_dump() for k, q in questions.items()},
    }
    await respect_cooldown()
    started = time.perf_counter()
    response = await _post(body)
    payload = response.json()
    raw_answers = payload.get("answers") or {}
    missing = [k for k in questions if k not in raw_answers]
    if missing:
        raise ValueError(f"decisions answered without {missing} (trace {trace_name})")
    decisions = Decisions(
        answers={k: _ANSWER.validate_python(_typed(v)) for k, v in raw_answers.items()},
        usage=Usage.model_validate(payload.get("usage") or {}),
        model=str(payload.get("model") or settings.prism_model_decide),
        id=str(payload.get("id") or ""),
    )
    elapsed_ms = round((time.perf_counter() - started) * 1000)
    logger.info(
        "decision",
        trace=trace_name,
        model=decisions.model,
        input_tokens=decisions.usage.input_tokens,
        cost=decisions.usage.cost,
        ms=elapsed_ms,
        **(metadata or {}),
    )
    if lf := get_langfuse():
        lf.update_current_generation(
            name=trace_name,
            model=decisions.model,
            input=body,
            output=payload.get("answers"),
            usage_details={"input": decisions.usage.input_tokens, "output": decisions.usage.output_tokens},
            cost_details={"total": decisions.usage.cost},
            metadata=metadata,
        )
    return decisions


async def _post(body: dict[str, Any]) -> httpx.Response:
    url = _decisions_url()
    last: Exception | None = None
    for attempt in range(_RETRIES + 1):
        try:
            response = await _get_client().post(url, json=body, headers=_headers())
        except httpx.HTTPError as exc:  # timeout, connect error — transient
            last = exc
        else:
            if response.status_code < 400:
                return response
            if response.status_code in QUOTA_STATUS:
                start_cooldown(response.status_code, response.text, get_settings().prism_model_decide)
                raise LlmQuotaError(f"decisions {response.status_code}: {response.text[:200]}")
            if response.status_code < 500:
                raise ValueError(f"decisions {response.status_code}: {response.text[:300]}")
            last = ConnectionError(f"decisions {response.status_code}: {response.text[:200]}")
        if attempt < _RETRIES:
            await asyncio.sleep(_RETRY_BACKOFF_S * (attempt + 1))
    raise ConnectionError(f"decisions unavailable after {_RETRIES + 1} attempts: {last}") from last
