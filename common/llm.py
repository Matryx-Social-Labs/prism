"""Model-agnostic LLM client — Ollama Cloud via its OpenAI-compatible API.

All chat models go through the langfuse.openai drop-in wrapper so every
call is traced (model, tokens, latency) without per-call code. Import
order matters: langfuse must wrap openai before any client is created
(see .claude/skills/langfuse guidance).
"""

import json
import logging
from typing import Any

# langfuse.openai must be imported before/instead of plain openai
from langfuse.openai import AsyncOpenAI  # noqa: I001
from pydantic import BaseModel

from common.config import get_settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


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

    Uses Ollama's OpenAI-compatible structured outputs (response_format json_schema).
    Retries once on invalid JSON — schema-constrained decoding makes that rare.
    """
    client = get_llm()
    schema = output_model.model_json_schema()
    kwargs: dict[str, Any] = {
        "model": model,
        "messages": messages,
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
        response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content or ""
        try:
            return output_model.model_validate(json.loads(content))
        except Exception as e:  # invalid JSON or schema mismatch
            last_err = e
            logger.warning(
                "structured_chat parse failed (attempt %d/%d) name=%s: %s",
                attempt + 1,
                max_retries,
                trace_name,
                e,
            )
    raise ValueError(f"structured_chat failed after {max_retries} attempts: {last_err}")


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
    response = await client.chat.completions.create(**kwargs)
    return response.choices[0].message.content or ""
