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
_WEEKLY_COOLDOWN_SECONDS = 900  # weekly-limit 429s: don't poke every 2 minutes
_cooldown_until = 0.0


class LlmQuotaError(ConnectionError):
    """Provider quota exhausted. Subclasses ConnectionError deliberately:
    stream consumers treat it as transient — the message stays pending and
    is redelivered, so the pipeline self-heals when the quota resets."""


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
        _client = AsyncOpenAI(base_url=base_url, api_key=api_key, default_headers=headers)
    return _client


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

    last_err: Exception | None = None
    for attempt in range(max_retries):
        await _respect_cooldown()
        try:
            response = await client.chat.completions.create(**kwargs)
        except Exception as e:
            _maybe_start_cooldown(e)
            if isinstance(e, APIStatusError) and e.status_code in _QUOTA_STATUS:
                raise LlmQuotaError(f"llm quota exhausted ({e.status_code})") from e
            raise
        content = response.choices[0].message.content or ""
        try:
            return output_model.model_validate(_parse_json_loose(content))
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
    raise ValueError(f"structured_chat failed after {max_retries} attempts: {last_err}")


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
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            return json.loads(text[start : end + 1])
        raise


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
