"""RSS collectors for the cyber beachhead (Tier 3-style own collectors)."""

import asyncio
import logging
import time
from datetime import UTC, datetime

import feedparser
import httpx

from common.schemas import RawItemEnvelope
from ingestion.base import persist_envelopes

logger = logging.getLogger(__name__)

FEEDS = {
    "thehackernews": "https://feeds.feedburner.com/TheHackersNews",
    "bleepingcomputer": "https://www.bleepingcomputer.com/feed/",
}


async def collect() -> int:
    inserted_total = 0
    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers={"User-Agent": "prism-prototype/0.1"}) as client:
        for slug, feed_url in FEEDS.items():
            try:
                response = await client.get(feed_url)
                response.raise_for_status()
                parsed = await asyncio.to_thread(feedparser.parse, response.text)
            except Exception:
                logger.exception("rss fetch failed for %s", slug)
                continue

            envelopes: list[RawItemEnvelope] = []
            for entry in parsed.entries:
                external_id = entry.get("id") or entry.get("link")
                if not external_id:
                    continue
                summary = entry.get("summary", "")
                envelopes.append(
                    RawItemEnvelope(
                        source_slug=slug,
                        source_type="rss",
                        external_id=external_id,
                        url=entry.get("link"),
                        title=entry.get("title", "(untitled)"),
                        body=_strip_html(summary) or None,
                        language="en",
                        published_at=_entry_datetime(entry),
                        raw={k: str(v)[:2000] for k, v in dict(entry).items()},
                    )
                )
            inserted = await persist_envelopes(envelopes)
            inserted_total += inserted
            logger.info("rss %s: %d new of %d entries", slug, inserted, len(envelopes))
    return inserted_total


def _entry_datetime(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(time.mktime(parsed), tz=UTC)


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", text).strip()
