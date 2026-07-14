"""Langfuse client access and prompt fetching with local fallbacks.

Prompts are managed in Langfuse (versioned, labeled `production`); local
fallback files in common/prompts/fallbacks/ keep the pipeline running if
Langfuse is unreachable (prompt-management "guaranteed availability").
"""

import json
import logging
from pathlib import Path

from langfuse import get_client, observe  # noqa: F401  (observe re-exported for stages)

from common.config import get_settings

logger = logging.getLogger(__name__)

FALLBACK_DIR = Path(__file__).parent / "prompts" / "fallbacks"


def get_langfuse():
    return get_client()


def fetch_prompt(name: str, *, prompt_type: str = "chat"):
    """Fetch a Langfuse-managed prompt by name (label `production`).

    Falls back to the local file of the same name if Langfuse is not
    configured or unreachable. Returns a Langfuse prompt object either way
    (the SDK wraps the fallback), so callers can .compile() and pass it as
    langfuse_prompt= for trace linking.
    """
    fallback = _load_fallback(name, prompt_type)
    settings = get_settings()
    if not settings.langfuse_enabled:
        return _LocalPrompt(name, fallback, prompt_type)
    try:
        return get_client().get_prompt(name, type=prompt_type, fallback=fallback)
    except Exception:
        logger.exception("Langfuse get_prompt(%s) failed; using local fallback", name)
        return _LocalPrompt(name, fallback, prompt_type)


def _load_fallback(name: str, prompt_type: str):
    if prompt_type == "chat":
        path = FALLBACK_DIR / f"{name}.json"
        return json.loads(path.read_text())
    path = FALLBACK_DIR / f"{name}.txt"
    return path.read_text()


class _LocalPrompt:
    """Minimal stand-in matching the parts of Langfuse's prompt API we use."""

    def __init__(self, name: str, prompt, prompt_type: str):
        self.name = name
        self.prompt = prompt
        self.type = prompt_type
        self.version = 0
        self.labels: list[str] = ["local-fallback"]
        self.config: dict = {}

    def compile(self, **variables):
        if self.type == "chat":
            return [
                {"role": m["role"], "content": _substitute(m["content"], variables)}
                for m in self.prompt
            ]
        return _substitute(self.prompt, variables)


def _substitute(template: str, variables: dict) -> str:
    out = template
    for key, value in variables.items():
        out = out.replace("{{" + key + "}}", str(value))
    return out
