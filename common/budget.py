"""The LLM balance as a fact the pipeline can read, not a failure it discovers.

Enrichment stopped for eleven hours on 2026-09-16/17 because the OpenRouter
balance reached zero and the only signal was a 402 in the worker log. The
collectors kept running, so the queue grew into a bill for the moment the
balance came back. Now the worker asks OpenRouter for the balance on an
interval, keeps the answer in Redis for anyone to read (the admin status
route, the ingestion gate), and ingestion stops COLLECTING — not just
enriching — under a floor, so a stall never builds a backlog.

Absence of evidence never acts: an unreachable OpenRouter leaves the last
known balance in place and, if there never was one, does not stop anything.
"""

import json
import time

import httpx

from common.config import get_settings
from common.logging import get_logger
from common.stream import get_redis

logger = get_logger(__name__)

KEY = "budget:openrouter"
CREDITS_URL = "https://openrouter.ai/api/v1/credits"


async def refresh() -> dict | None:
    """Ask OpenRouter; record {balance, credits, usage, at}; return it. None when unreachable."""
    settings = get_settings()
    if settings.llm_provider != "openrouter" or not settings.openrouter_api_key:
        return None
    try:
        async with httpx.AsyncClient(timeout=15) as http:
            r = await http.get(CREDITS_URL, headers={"Authorization": f"Bearer {settings.openrouter_api_key}"})
            r.raise_for_status()
            d = r.json()["data"]
    except Exception as e:  # noqa: BLE001 — a balance we cannot read is not a balance of zero
        logger.warning("budget_refresh_failed", error=str(e)[:200])
        return None
    rec = {
        "credits": float(d["total_credits"]),
        "usage": float(d["total_usage"]),
        "balance": round(float(d["total_credits"]) - float(d["total_usage"]), 4),
        "at": time.time(),
    }
    await get_redis().set(KEY, json.dumps(rec))
    logger.info("budget_refreshed", balance=rec["balance"])
    return rec


async def current() -> dict | None:
    """The last recorded balance; None when none was recorded or Redis is not
    there to ask — a balance we cannot read is not a balance under the floor."""
    try:
        raw = await get_redis().get(KEY)
    except Exception as e:  # noqa: BLE001
        logger.warning("budget_read_failed", error=str(e)[:200])
        return None
    if not raw:
        return None
    return json.loads(raw if isinstance(raw, str) else raw.decode())


def below_floor(rec: dict | None) -> bool:
    """True only on evidence: a recorded balance under the configured floor."""
    floor = get_settings().prism_llm_budget_floor_usd
    return bool(rec) and floor > 0 and rec["balance"] < floor
