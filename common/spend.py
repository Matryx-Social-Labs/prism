"""What the models cost, per stage, per day — the ledger /admin/spend reads.

Until 2026-09-27 nobody could say where the OpenRouter bill went: the chat client
logged no usage, Langfuse is off, and Railway keeps four hours of logs. The
audit that day had to rebuild it from call counts and token calibration (88%
of the week attributed). This records it as it happens instead: every chat
call (common/llm.structured_chat) and every Jev decision (common/decisions)
adds its tokens and OpenRouter's own cost to one Redis hash per UTC day, keyed
by stage (the trace name) and model.

Recording never fails a call: a Redis error is logged and the call proceeds.
Days before this shipped are absent, not zero.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from common.logging import get_logger
from common.stream import get_redis

logger = get_logger(__name__)

KEEP_DAYS = 120
_FIELDS = ("calls", "input_tokens", "cached_tokens", "output_tokens", "cost")


def _key(day: dt.date) -> str:
    return f"spend:{day.isoformat()}"


def usage_of(response: Any) -> tuple[int, int, int, float | None]:
    """(input, cached, output, cost) off an OpenAI-shaped completion. OpenRouter
    puts `cost` beside the standard usage fields; None when it did not."""
    u = getattr(response, "usage", None)
    if u is None:
        return 0, 0, 0, None
    details = getattr(u, "prompt_tokens_details", None)
    cached = (getattr(details, "cached_tokens", None) if details is not None else None) or 0
    cost = (getattr(u, "model_extra", None) or {}).get("cost")
    return u.prompt_tokens or 0, cached, u.completion_tokens or 0, float(cost) if cost is not None else None


async def record(
    stage: str, model: str, *, input_tokens: int = 0, cached_tokens: int = 0, output_tokens: int = 0,
    cost: float | None = None, when: dt.datetime | None = None,
) -> None:
    day = (when or dt.datetime.now(dt.UTC)).date()
    prefix = f"{stage or 'unnamed'}|{model}|"
    try:
        pipe = get_redis().pipeline(transaction=False)
        key = _key(day)
        pipe.hincrby(key, prefix + "calls", 1)
        pipe.hincrby(key, prefix + "input_tokens", int(input_tokens))
        pipe.hincrby(key, prefix + "cached_tokens", int(cached_tokens))
        pipe.hincrby(key, prefix + "output_tokens", int(output_tokens))
        pipe.hincrbyfloat(key, prefix + "cost", float(cost or 0.0))
        pipe.expire(key, KEEP_DAYS * 86400)
        await pipe.execute()
    except Exception as exc:  # noqa: BLE001 — the ledger is observability; it never costs a call
        logger.warning("spend_record_failed", stage=stage, error=str(exc)[:160])


async def record_response(response: Any, stage: str, model: str) -> None:
    """Log one chat call's usage and add it to the day's ledger."""
    inp, cached, out, cost = usage_of(response)
    served = getattr(response, "model", None) or model
    # Which endpoint served it: a cache lives per endpoint, so this is what
    # explains a cached share that suddenly drops.
    provider = (getattr(response, "model_extra", None) or {}).get("provider")
    logger.info("llm_call", trace=stage, model=served, provider=provider, input_tokens=inp, cached_tokens=cached,
                output_tokens=out, cost=cost)
    await record(stage, served, input_tokens=inp, cached_tokens=cached, output_tokens=out, cost=cost)


async def days(n: int, today: dt.date | None = None) -> list[dict]:
    """The last n UTC days, newest first: {day, cost, calls, stages: [...]}; a
    day with no ledger is returned with `recorded: False`, never as zero."""
    today = today or dt.datetime.now(dt.UTC).date()
    wanted = [today - dt.timedelta(days=i) for i in range(n)]
    pipe = get_redis().pipeline(transaction=False)
    for d in wanted:
        pipe.hgetall(_key(d))
    raw = await pipe.execute()
    out = []
    for d, h in zip(wanted, raw, strict=True):
        stages: dict[tuple[str, str], dict] = {}
        for field, value in (h or {}).items():
            stage, model, metric = field.rsplit("|", 2)
            row = stages.setdefault((stage, model), {"stage": stage, "model": model, **dict.fromkeys(_FIELDS, 0)})
            row[metric] = float(value) if metric == "cost" else int(float(value))
        rows = sorted(stages.values(), key=lambda r: -r["cost"])
        out.append({
            "day": d.isoformat(),
            "recorded": bool(h),
            "cost": round(sum(r["cost"] for r in rows), 4),
            "calls": sum(r["calls"] for r in rows),
            "stages": [{**r, "cost": round(r["cost"], 5)} for r in rows],
        })
    return out
