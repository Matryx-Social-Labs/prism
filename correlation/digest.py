"""Market Pulse — an LLM-synthesized read across the day's top market stories.

This is the value the feed can't give: not a ranked list, but a short editor's
synthesis of the through-lines. Generated at most once per TTL and cached in
Redis (single-flight across replicas), so a burst of viewers costs one LLM call.
No table/migration — the digest is derived and cheap to regenerate.
"""

import json
from datetime import UTC, datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field
from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.locks import single_flight
from common.logging import get_logger
from common.observability import fetch_prompt
from common.stream import get_redis

logger = get_logger(__name__)

CACHE_KEY = "digest:markets"
CACHE_TTL = 3 * 60 * 60  # 3h — the pulse is a rolling read, not real-time
TOP_N = 12


class Mover(BaseModel):
    ticker: str
    note: str = ""


class MarketDigestLLM(BaseModel):
    # Ollama doesn't enforce json field names; keep them distinctive + tolerant.
    model_config = ConfigDict(populate_by_name=True)
    headline: str = Field(validation_alias=AliasChoices("headline", "title"))
    narrative: str = Field(default="", validation_alias=AliasChoices("narrative", "body", "text"))
    movers: list[Mover] = Field(default_factory=list)


async def _top_stories() -> list[dict]:
    """Recent market-moving events (finance/business), newest first."""
    async with session_scope() as s:
        rows = (
            await s.execute(
                text(
                    """
                    SELECT id, title, summary, projection
                    FROM events
                    WHERE sector IN ('finance', 'business')
                      AND summary IS NOT NULL
                    ORDER BY last_updated_at DESC
                    LIMIT :n
                    """
                ),
                {"n": TOP_N},
            )
        ).mappings().all()
    out = []
    for r in rows:
        fin = (r["projection"] or {}).get("finance") or {}
        out.append(
            {
                "id": str(r["id"]),
                "title": r["title"],
                "summary": r["summary"],
                "tickers": (fin.get("tickers") or [])[:6],
                "catalyst": fin.get("catalyst"),
            }
        )
    return out


def _format(stories: list[dict]) -> str:
    lines = []
    for st in stories:
        tk = f" [{', '.join('$' + t for t in st['tickers'])}]" if st["tickers"] else ""
        cat = f" ({st['catalyst'].replace('_', ' ')})" if st["catalyst"] else ""
        lines.append(f"- {st['title']}{tk}{cat}\n  {st['summary']}")
    return "\n".join(lines)


async def _generate() -> dict | None:
    now = datetime.now(UTC).isoformat()
    stories = await _top_stories()
    if not stories:
        return {"headline": "Markets are quiet", "narrative": "No market-moving stories yet.", "movers": [], "event_ids": [], "generated_at": now}
    prompt = fetch_prompt("market-digest")
    messages = prompt.compile(stories=_format(stories))
    try:
        result = await structured_chat(
            model=get_settings().prism_model_correlate,
            messages=messages,
            output_model=MarketDigestLLM,
            trace_name="market-digest",
            metadata={"stage": "market-digest", "n": len(stories)},
            langfuse_prompt=prompt if prompt.version else None,
        )
    except Exception:
        # The Pulse is a pure LLM synthesis — if the model is unavailable (quota
        # exhausted, timeout), degrade to no-digest so the endpoint 204s and the
        # feed hides the card, instead of surfacing a 500 to every reader.
        logger.warning("market_digest_unavailable", stories=len(stories), exc_info=True)
        return None
    # Ground the movers: keep only tickers that actually appear in the source
    # events, so the digest can't surface a ticker the LLM inferred from context.
    real_tickers = {t.upper() for st in stories for t in st["tickers"]}
    movers = [m for m in result.movers if m.ticker.upper() in real_tickers]
    logger.info(
        "market_digest_generated", stories=len(stories), movers=len(movers), dropped=len(result.movers) - len(movers)
    )
    return {
        "headline": result.headline,
        "narrative": result.narrative,
        "movers": [m.model_dump() for m in movers],
        "event_ids": [st["id"] for st in stories],
        "generated_at": now,
    }


async def get_market_digest() -> dict | None:
    """Cached digest; regenerates once per TTL, single-flighted across replicas.
    Returns None when synthesis is unavailable (the route 204s and the feed hides
    the Pulse card) — never cache a failure, so it retries on the next request."""
    redis = get_redis()
    cached = await redis.get(CACHE_KEY)
    if cached:
        return json.loads(cached)

    async with single_flight(CACHE_KEY, ttl=60, wait_timeout=45.0) as leader:
        if not leader:
            cached = await redis.get(CACHE_KEY)
            if cached:
                return json.loads(cached)
        digest = await _generate()
        if digest is None:
            return None
        await redis.set(CACHE_KEY, json.dumps(digest), ex=CACHE_TTL)
        return digest
