"""GDELT DOC 2.0 collector (free, no key) — worldwide news breadth.

Queries security-relevant coverage. GDELT returns titles/URLs (no body);
full text is fetched post-relevance-gate in enrichment (cost discipline:
expensive work only past the gate).
"""

import asyncio
import hashlib
import logging
from datetime import datetime

import httpx

from common.schemas import RawItemEnvelope
from ingestion.base import persist_envelopes

logger = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
SLUG = "gdelt"
# One query per beachhead lens; new lenses add a line, not a collector.
QUERIES = {
    "cyber": '(cyberattack OR ransomware OR "data breach" OR "zero-day" OR "vulnerability exploited")',
    "finance": '("earnings report" OR "guidance raise" OR "rate decision" OR "merger agreement" OR "SEC charges" OR "stock plunges" OR "stock surges")',
}


async def collect(timespan: str = "1d", max_records: int = 60) -> int:
    inserted_total = 0
    async with httpx.AsyncClient(timeout=60) as client:
        for i, (query_slug, query) in enumerate(QUERIES.items()):
            if i:
                await asyncio.sleep(10)  # GDELT free tier rate-limits aggressively
            params = {
                "query": query,
                "mode": "ArtList",
                "format": "json",
                "maxrecords": str(max_records),
                "timespan": timespan,
                "sort": "DateDesc",
            }
            try:
                response = await client.get(GDELT_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except Exception:
                # GDELT free API rate-limits aggressively; skip this query, next
                # scheduled run picks it up.
                logger.warning("gdelt %s query failed; skipping", query_slug, exc_info=True)
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
            logger.info("gdelt %s: %d new of %d candidates", query_slug, inserted, len(envelopes))
    return inserted_total


def _parse_seendate(value: str | None) -> datetime | None:
    # GDELT format: 20260714T093000Z
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ")
    except ValueError:
        return None
