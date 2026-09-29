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

from common import alerts, spend
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


# Days of spend left above the floor at which founders are warned: enough to
# add credit before collection stops.
RUNWAY_WARN_DAYS = 2


# Hours of today's ledger before its pace counts: an hour's burst is not a day.
MIN_TODAY_HOURS = 3


async def _daily_spend(now: float | None = None) -> float | None:
    """Dollars a day: the mean of the last two complete ledger days, or today's
    pace when that is higher — after a pause the complete days read ~$0 and
    would never warn. None when nothing was recorded."""
    today, *before = await spend.days(3)
    days = [d for d in before if d["recorded"]]
    rate = sum(d["cost"] for d in days) / len(days) if days else 0.0
    hours = ((now or time.time()) % 86400) / 3600
    if today["recorded"] and hours >= MIN_TODAY_HOURS:
        rate = max(rate, today["cost"] * 24 / hours)
    return rate or None


async def warn_if_low(rec: dict | None) -> None:
    """Email the founders when collection has stopped, or will within
    RUNWAY_WARN_DAYS at the recent daily spend. Nothing on no evidence."""
    if not rec:
        return
    floor = get_settings().prism_llm_budget_floor_usd
    if below_floor(rec):
        await alerts.notify(
            "budget-floor",
            "News collection has stopped: add OpenRouter credit",
            f"The OpenRouter balance is ${rec['balance']:.2f}, under the ${floor:.2f} floor, so the worker has "
            "stopped collecting news. It resumes on its own about 20 minutes after a top-up (the balance is re-read every 15).",
        )
        return
    daily = await _daily_spend()
    if daily and (rec["balance"] - floor) / daily < RUNWAY_WARN_DAYS:
        left = (rec["balance"] - floor) / daily
        await alerts.notify(
            "budget-runway",
            f"About {left:.1f} days of LLM credit left",
            f"The OpenRouter balance is ${rec['balance']:.2f}; at ${daily:.2f} a day, collection stops at the "
            f"${floor:.2f} floor in about {left:.1f} days.",
        )
