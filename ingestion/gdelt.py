"""GDELT DOC 2.0 collector (free, no key) — worldwide news breadth.

Queries security-relevant coverage. GDELT returns titles/URLs (no body);
full text is fetched post-relevance-gate in enrichment (cost discipline:
expensive work only past the gate).
"""

import hashlib
import logging
from datetime import datetime

import httpx

from common.schemas import RawItemEnvelope
from ingestion.base import persist_envelopes

logger = logging.getLogger(__name__)

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
SLUG = "gdelt"
QUERY = '(cyberattack OR ransomware OR "data breach" OR "zero-day" OR "vulnerability exploited")'


async def collect(timespan: str = "1d", max_records: int = 75) -> int:
    params = {
        "query": QUERY,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(max_records),
        "timespan": timespan,
        "sort": "DateDesc",
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(GDELT_URL, params=params)
        response.raise_for_status()
        try:
            data = response.json()
        except ValueError:
            logger.warning("gdelt returned non-JSON payload; skipping run")
            return 0

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
                raw=article,
            )
        )

    inserted = await persist_envelopes(envelopes)
    logger.info("gdelt: %d new of %d candidates", inserted, len(envelopes))
    return inserted


def _parse_seendate(value: str | None) -> datetime | None:
    # GDELT format: 20260714T093000Z
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y%m%dT%H%M%SZ")
    except ValueError:
        return None
