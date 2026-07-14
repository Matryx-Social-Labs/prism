"""Model-agnostic LLM client — Ollama Cloud via its OpenAI-compatible API.

All chat models go through the langfuse.openai drop-in wrapper so every
call is traced (model, tokens, latency) without per-call code. Import
order matters: langfuse must wrap openai before any client is created
(see .claude/skills/langfuse guidance).
"""

import asyncio
import json
import logging
import time
from typing import Any

# langfuse.openai must be imported before/instead of plain openai
from langfuse.openai import AsyncOpenAI  # noqa: I001
from openai import APIStatusError
from pydantic import BaseModel

from common.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None

# Global cooldown: when the provider rejects with 401/403/429 (Ollama Cloud
# returns 401 while the GPU-time session quota is exhausted), all LLM calls
# pause instead of hammering the API hundreds of times per minute. Items that
# fail during the window are re-driven by the ingestion requeue.
_QUOTA_STATUS = {401, 403, 429}
_COOLDOWN_SECONDS = 120
_cooldown_until = 0.0


async def _respect_cooldown() -> None:
    wait = _cooldown_until - time.monotonic()
    if wait > 0:
        await asyncio.sleep(wait)


def _maybe_start_cooldown(error: Exception) -> None:
    global _cooldown_until
    if isinstance(error, APIStatusError) and error.status_code in _QUOTA_STATUS:
        _cooldown_until = time.monotonic() + _COOLDOWN_SECONDS
        logger.warning(
            "LLM provider returned %d (quota/auth) — pausing all LLM calls %ds",
            error.status_code,
            _COOLDOWN_SECONDS,
        )


def get_llm() -> AsyncOpenAI:
    global _client
    if _client is None:
        settings = get_settings()
        _client = AsyncOpenAI(
            base_url=settings.ollama_base_url,
            api_key=settings.ollama_api_key or "ollama",
        )
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
    max_retries: int = 2,
) -> T:
    """Chat completion constrained to a JSON schema, validated into a Pydantic model.

    Belt and braces: the schema is embedded in the prompt (providers like
    Ollama Cloud don't reliably enforce response_format json_schema — models
    were observed inventing field names) AND passed as response_format for
    providers that do enforce it. Parsing tolerates markdown fences; retries
    feed the validation error back to the model.
    """
    client = get_llm()
    schema = output_model.model_json_schema()
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
            raise
        content = response.choices[0].message.content or ""
        try:
            return output_model.model_validate(_parse_json_loose(content))
        except Exception as e:  # invalid JSON or schema mismatch
            last_err = e
            logger.warning(
                "structured_chat parse failed (attempt %d/%d) name=%s: %s",
                attempt + 1,
                max_retries,
                trace_name,
                e,
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
