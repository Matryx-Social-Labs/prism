"""Model-agnostic LLM client — Ollama Cloud via its OpenAI-compatible API.

All chat models go through the langfuse.openai drop-in wrapper so every
call is traced (model, tokens, latency) without per-call code. Import
order matters: langfuse must wrap openai before any client is created
(see .claude/skills/langfuse guidance).
"""

import asyncio
import json
import time
from typing import Any

# langfuse.openai must be imported before/instead of plain openai
from langfuse.openai import AsyncOpenAI  # noqa: I001
from openai import APIStatusError
from pydantic import BaseModel

from common.config import get_settings
from common.logging import get_logger

logger = get_logger(__name__)

_client: AsyncOpenAI | None = None

# Global cooldown: when the provider rejects for a billing/quota reason, all LLM
# calls pause instead of hammering the API hundreds of times per minute. Items
# that fail during the window stay pending on the stream and are redelivered, so
# the pipeline self-heals once the account recovers.
#   401/403 — auth/quota (Ollama Cloud returns 401 when GPU-time quota is spent)
#   402     — OpenRouter "insufficient credits" (manual top-up; treat as a pause,
#             not a per-message traceback storm)
#   429     — rate/weekly limit
_QUOTA_STATUS = {401, 402, 403, 429}
_COOLDOWN_SECONDS = 120
# Per-request ceiling; see get_llm for why an explicit one matters.
LLM_TIMEOUT_SECONDS = 90.0
_WEEKLY_COOLDOWN_SECONDS = 900  # weekly-limit 429s: don't poke every 2 minutes
_cooldown_until = 0.0


class LlmQuotaError(ConnectionError):
    """Provider quota exhausted. Subclasses ConnectionError deliberately:
    stream consumers treat it as transient — the message stays pending and
    is redelivered, so the pipeline self-heals when the quota resets."""


class LlmEmptyResponse(ConnectionError):
    """The provider answered with no content (finish_reason "error", content
    null). Seen intermittently from Google through OpenRouter on 2026-09-17:
    the same request succeeds seconds later. A ConnectionError so the stream
    consumer keeps the message rather than dropping the article as a parse
    failure — which is what it did, six times in one log window."""


async def _respect_cooldown() -> None:
    wait = _cooldown_until - time.monotonic()
    if wait > 0:
        await asyncio.sleep(wait)


def _maybe_start_cooldown(error: Exception) -> None:
    global _cooldown_until
    if isinstance(error, APIStatusError) and error.status_code in _QUOTA_STATUS:
        pause = _WEEKLY_COOLDOWN_SECONDS if "weekly" in str(error).lower() else _COOLDOWN_SECONDS
        _cooldown_until = time.monotonic() + pause
        logger.warning("llm_quota_cooldown", status=error.status_code, pause_s=pause)


def get_llm() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        if settings.llm_provider == "openrouter":
            base_url = settings.openrouter_base_url
            api_key = settings.openrouter_api_key or "missing-openrouter-key"
            # Optional attribution shown on the OpenRouter dashboard.
            headers = {"HTTP-Referer": settings.prism_web_url, "X-Title": "Prism"}
        else:  # ollama fallback
            base_url = settings.ollama_base_url
            api_key = settings.ollama_api_key or "ollama"
            headers = None
        # EXPLICIT TIMEOUT. The client default is 600s, and a hung call holds an
        # enrichment concurrency slot for all of it. With 12 slots and a stream
        # batch of 12, a handful of slow calls stalls the whole batch — which is
        # what a cold-start measurement on 2026-09-03 showed: the relevance gate
        # approved ~6,000 items/hour while enrichment consumed ~180, a 33x gap
        # that grew the queue ~5,800/hour and never drained.
        #
        # 90s is well past a normal extract (a few seconds) and well short of the
        # batch stall. A call that exceeds it raises, the message stays pending on
        # the stream and is redelivered, so the work is retried rather than lost.
        _client = AsyncOpenAI(
            base_url=base_url, api_key=api_key, default_headers=headers,
            timeout=LLM_TIMEOUT_SECONDS, max_retries=2,
        )
    return _client


# No thinking aloud: the ceiling is spent on the answer. For the stages whose
# output is a JSON record of the article, not a judgement. Measured 2026-09-17
# on one gate call: qwen3.7-plus 758 output tokens (690 of them reasoning,
# 13.3s) by default, 64 tokens and 2.0s with this; qwen3.7-flash 743 -> 51;
# gemini-3.1-flash-lite reasons nothing either way.
REASONING_OFF: dict[str, Any] = {"enabled": False}


async def structured_chat[T: BaseModel](
    *,
    model: str,
    messages: list[dict[str, str]],
    output_model: type[T],
    trace_name: str,
    metadata: dict[str, Any] | None = None,
    langfuse_prompt: Any = None,
    temperature: float | None = None,
    max_tokens: int = 8192,
    max_retries: int = 2,
    prune_fields: set[str] | None = None,
    reasoning: dict[str, Any] | None = None,
) -> T:
    """Chat completion constrained to a JSON schema, validated into a Pydantic model.

    Belt and braces: the schema is embedded in the prompt (providers like
    Ollama Cloud don't reliably enforce response_format json_schema — models
    were observed inventing field names) AND passed as response_format for
    providers that do enforce it. Parsing tolerates markdown fences; retries
    feed the validation error back to the model.

    prune_fields drops optional properties from the schema shown to the model
    (across the top level and every $def) so it doesn't spend output tokens
    generating fields the caller discards. Only pass fields that have a default
    on the model — validation still fills them in.

    reasoning is OpenRouter's control over thinking tokens, which on most
    providers share max_tokens and are billed. A structured extraction gains
    nothing from a model thinking aloud first: pass REASONING_OFF and the
    ceiling is spent on the JSON. A model that marks reasoning mandatory
    rejects "off" and gets the smallest effort instead, so the choice never
    costs an article.
    """
    client = get_llm()
    schema = output_model.model_json_schema()
    if prune_fields:
        _prune_schema_props(schema, prune_fields)
    schema_msg = {
        "role": "system",
        "content": (
            "Respond with a single JSON object only — no prose, no markdown fences. "
            "It must match this JSON Schema exactly (use these exact property names; "
            "include every required property):\n" + json.dumps(schema)
        ),
    }
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": [*messages, schema_msg],
        "response_format": {
            "type": "json_schema",
            "json_schema": {"name": output_model.__name__, "schema": schema},
        },
        "max_tokens": max_tokens,  # headroom so a large nested JSON isn't truncated mid-string
        "name": trace_name,
        "metadata": metadata or {},
    }
    if langfuse_prompt is not None:
        kwargs["langfuse_prompt"] = langfuse_prompt
    if temperature is not None:
        kwargs["temperature"] = temperature
    if reasoning is not None and get_settings().llm_provider == "openrouter":
        kwargs["extra_body"] = {"reasoning": reasoning}

    last_err: Exception | None = None
    for attempt in range(max_retries):
        await _respect_cooldown()
        try:
            response = await client.chat.completions.create(**kwargs)
        except APIStatusError as e:
            if e.status_code == 400 and "extra_body" in kwargs and "reasoning" in str(e).lower():
                # A model that marks reasoning mandatory (glm-5.3-flash, gpt-5-nano)
                # rejects "off"; it accepts the smallest effort, which measured at
                # ~40-70 output tokens against 230-460 with the default.
                logger.info("reasoning_control_rejected", model=model, trace=trace_name)
                kwargs["extra_body"] = {"reasoning": {"effort": "minimal"}}
                response = await client.chat.completions.create(**kwargs)
            else:
                _maybe_start_cooldown(e)
                if e.status_code in _QUOTA_STATUS:
                    raise LlmQuotaError(f"llm quota exhausted ({e.status_code})") from e
                raise
        except Exception as e:
            _maybe_start_cooldown(e)
            raise
        choice = response.choices[0]
        content = choice.message.content or ""
        if not content.strip():
            # Not a parse failure: the provider gave nothing. Try once more
            # after a beat, then hand the message back to the stream.
            last_err = LlmEmptyResponse(f"empty response (finish_reason={choice.finish_reason})")
            logger.warning("llm_empty_response", attempt=attempt + 1, trace=trace_name, finish_reason=choice.finish_reason, model=model)
            await asyncio.sleep(2)
            continue
        try:
            parsed = _parse_json_loose(content)
        except Exception as e:
            parsed, e_parse = None, e
        else:
            e_parse = None

        # The single most common failure (50 of 129 observed in production): the
        # model returns the SCHEMA WE SENT rather than an instance of it. The
        # generic path handles that badly twice over — it reports the symptom
        # ("shared: Field required") instead of the cause, and it appends the
        # echoed schema back into the conversation, so the retry sees the schema
        # one more time and tends to echo it again. Name it instead, and do not
        # quote it back.
        if parsed is not None and _looks_like_json_schema(parsed):
            last_err = ValueError("model returned the JSON Schema instead of an instance of it")
            logger.warning(
                "structured_output_schema_echoed",
                attempt=attempt + 1,
                max_retries=max_retries,
                trace=trace_name,
            )
            kwargs["messages"] = [
                *kwargs["messages"],
                {
                    "role": "user",
                    "content": (
                        "You returned the JSON Schema itself. Do not repeat the schema. "
                        "Return a single JSON object that is an INSTANCE of it: real values "
                        "for this article, no '$defs', no 'properties', no 'type' metadata."
                    ),
                },
            ]
            continue

        try:
            return output_model.model_validate(parsed if e_parse is None else _parse_json_loose(content))
        except Exception as e:  # invalid JSON or schema mismatch
            last_err = e
            logger.warning(
                "structured_output_parse_failed",
                attempt=attempt + 1,
                max_retries=max_retries,
                trace=trace_name,
                error=str(e)[:300],
            )
            # Feed the failure back so the retry can correct field names/shape.
            kwargs["messages"] = [
                *kwargs["messages"],
                {"role": "assistant", "content": content[:2000]},
                {
                    "role": "user",
                    "content": f"That JSON failed validation: {e}. "
                    "Return a corrected JSON object matching the schema exactly.",
                },
            ]
    if isinstance(last_err, LlmEmptyResponse):
        raise last_err
    raise ValueError(f"structured_chat failed after {max_retries} attempts: {last_err}")


def _looks_like_json_schema(obj: Any) -> bool:
    """True when `obj` is the schema rather than an instance of it.

    Keyed on markers that a real extraction cannot carry: `$defs` and `$schema`
    are schema-only, and a top-level `properties` dict alongside `type: "object"`
    is the shape of a schema node. An ArticleExtraction instance has none of them.
    """
    if not isinstance(obj, dict):
        return False
    if "$defs" in obj or "$schema" in obj:
        return True
    return obj.get("type") == "object" and isinstance(obj.get("properties"), dict)


def _prune_schema_props(schema: dict[str, Any], fields: set[str]) -> None:
    """Remove named properties from every object node in a JSON Schema, incl.
    the $defs pydantic emits for nested models. Mutates in place. The referenced
    $def (e.g. ExtractedImpact) is left orphaned — harmless, since no property
    points at it anymore so the model is never asked to produce it."""
    for node in [schema, *(schema.get("$defs") or {}).values()]:
        props = node.get("properties")
        if isinstance(props, dict):
            for f in fields:
                props.pop(f, None)
        req = node.get("required")
        if isinstance(req, list):
            node["required"] = [r for r in req if r not in fields]


def _parse_json_loose(content: str) -> Any:
    """Parse model output as JSON, tolerating markdown fences and prose."""
    text = content.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0].strip()
    def _braces() -> Any:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise ValueError("no JSON object in model output")

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return _braces()
    # A BARE SCALAR IS NOT AN INSTANCE OF A MODEL, and returning one here short-
    # circuits the brace scan below. Observed live: the extract model answered
    # `-8.039215789473683` and `-1e-05` — a stray sentiment value with the object
    # nowhere in sight — and pydantic then reported "Input should be a valid
    # dictionary", which reads like a schema mismatch rather than "the model did
    # not answer". Falling through lets an object embedded in prose still be
    # found, and where there is none the error names the real problem.
    if not isinstance(parsed, dict):
        try:
            return _braces()
        except Exception:
            raise ValueError(
                f"model returned a bare {type(parsed).__name__}, not a JSON object"
            ) from None
    return parsed


async def plain_chat(
    *,
    model: str,
    messages: list[dict[str, str]],
    trace_name: str,
    metadata: dict[str, Any] | None = None,
    langfuse_prompt: Any = None,
) -> str:
    client = get_llm()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "name": trace_name,
        "metadata": metadata or {},
    }
    if langfuse_prompt is not None:
        kwargs["langfuse_prompt"] = langfuse_prompt
    await _respect_cooldown()
    try:
        response = await client.chat.completions.create(**kwargs)
    except Exception as e:
        _maybe_start_cooldown(e)
        raise
    return response.choices[0].message.content or ""
