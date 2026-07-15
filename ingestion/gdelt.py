"""GDELT DOC 2.0 collector (free, no key) — worldwide news breadth.

One query per coverage area (lens beachheads + world news for the general
reader); new coverage adds a line, not a collector. GDELT returns
titles/URLs (no body); full text is fetched post-relevance-gate in
enrichment (cost discipline: expensive work only past the gate).
"""

import asyncio
import hashlib
import random
from datetime import datetime

import httpx

from common.logging import get_logger
from common.schemas import RawItemEnvelope
from ingestion.base import persist_envelopes

logger = get_logger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
SLUG = "gdelt"
QUERIES = {
    "cyber": '(cyberattack OR ransomware OR "data breach" OR "zero-day" OR "vulnerability exploited")',
    "finance": '("earnings report" OR "guidance raise" OR "rate decision" OR "merger agreement" OR "SEC charges" OR "stock plunges" OR "stock surges")',
    "world": '(war OR ceasefire OR election OR summit OR sanctions OR "state of emergency" OR earthquake OR "peace talks")',
}
INTER_QUERY_GAP_S = 20  # GDELT free tier rate-limits aggressively


async def collect(timespan: str = "1d", max_records: int = 60) -> int:
    inserted_total = 0
    async with httpx.AsyncClient(timeout=60) as client:
        for i, (query_slug, query) in enumerate(QUERIES.items()):
            if i:
                await asyncio.sleep(INTER_QUERY_GAP_S)
            params = {
                "query": query,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": str(max_records),
                "timespan": timespan,
                "sort": "DateDesc",
            }
            data = await _fetch_with_backoff(client, params, query_slug)
            if data is None:
                continue

            envelopes: list[RawItemEnvelope] = []
            for article in data.get("articles", []):
                url = article.get("url")
                if not url:
                    continue
                envelopes.append(
                    RawItemEnvelope(
                        source_slug=SLUG,
                        source_type="news_api",
                        external_id=hashlib.sha256(url.encode()).hexdigest()[:32],
                        url=url,
                        title=article.get("title") or url,
                        body=None,  # GDELT gives no body; fetched later
                        language=(article.get("language") or "").lower()[:8] or None,
                        published_at=_parse_seendate(article.get("seendate")),
                        raw={**article, "prism_query": query_slug},
                    )
                )

            inserted = await persist_envelopes(envelopes)
            inserted_total += inserted
            logger.info(
                "collector_run",
                collector=f"gdelt:{query_slug}",
                new=inserted,
                candidates=len(envelopes),
            )
    return inserted_total


async def _fetch_with_backoff(
    client: httpx.AsyncClient, params: dict, query_slug: str
) -> dict | None:
    """One retry honoring Retry-After (plus jitter); skip on repeat failure.

    The next scheduled run picks up anything skipped, so failing soft here
    beats stalling the whole collector cycle.
    """
    for attempt in (1, 2):
        try:
            response = await client.get(GDELT_URL, params=params)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429 and attempt == 1:
                retry_after = _retry_after_seconds(e.response)
                wait = retry_after + random.uniform(1, 5)
                logger.warning(
                    "gdelt_rate_limited", query=query_slug, retry_in_s=round(wait, 1)
                )
                await asyncio.sleep(wait)
                continue
            logger.warning(
                "gdelt_query_failed", query=query_slug, status=e.response.status_code
            )
            return None
        except Exception:
            logger.warning("gdelt_query_failed", query=query_slug, exc_info=True)
            return None
    return None


def _retry_after_seconds(response: httpx.Response) -> float:
    try:
        return min(float(response.headers.get("Retry-After", 30)), 120.0)
    except ValueError:
        return 30.0


def _parse_seendate(value: str | None) -> datetime | None:
    # GDELT format: 20260714T093000Z
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ")
    except ValueError:
        return None
