"""Langfuse client access and prompt fetching with local fallbacks.

Prompts are managed in Langfuse (versioned, labeled `production`); local
fallback files in common/prompts/fallbacks/ keep the pipeline running if
Langfuse is unreachable (prompt-management "guaranteed availability").
"""

import functools
import inspect
import json
import logging
from pathlib import Path

from langfuse import get_client
from langfuse import observe as _sdk_observe

from common.config import get_settings

logger = logging.getLogger(__name__)

FALLBACK_DIR = Path(__file__).parent / "prompts" / "fallbacks"


def get_langfuse():
    """The Langfuse client, or None when tracing is off.

    Returns None rather than raising: callers are observability paths, and losing
    a trace must never take down the stage it was watching.
    """
    if not get_settings().langfuse_enabled:
        return None
    return get_client()


def observe(*dargs, **dkwargs):
    """Trace this stage — or, when tracing is off, be exactly the plain function.

    The self-hosted Langfuse scales to zero after 10 idle minutes, so a single
    background span wakes the whole stack (web + worker + ClickHouse + MinIO) and
    restarts billing. The gate therefore has to sit BEFORE the SDK is touched, not
    merely drop the span afterwards: `_sdk_observe` is applied lazily on the first
    ENABLED call, so with tracing off no client is ever constructed, no exporter
    thread starts, and nothing is queued for flush.

    Checked per call rather than at import so a process can be flipped without a
    redeploy, and so tests can toggle it without reimporting every stage module.
    """

    def decorate(fn):
        traced = None

        def _traced():
            nonlocal traced
            if traced is None:
                traced = _sdk_observe(*dargs, **dkwargs)(fn)
            return traced

        if inspect.iscoroutinefunction(fn):

            @functools.wraps(fn)
            async def awrapper(*args, **kwargs):
                if not get_settings().langfuse_enabled:
                    return await fn(*args, **kwargs)
                return await _traced()(*args, **kwargs)

            return awrapper

        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if not get_settings().langfuse_enabled:
                return fn(*args, **kwargs)
            return _traced()(*args, **kwargs)

        return wrapper

    return decorate


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
