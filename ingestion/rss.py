"""RSS collectors — professional beachheads, world news, and regional/topic feeds.

Outlet countries and state-affiliation labels are set in ingestion/seed.py;
distinct origins feed the Both-Sides perspective grouping and the
coverage-origin balance on international stories.

Feeds with a `sector` set are single-topic: their items are classified
deterministically (no gate LLM, no classifier LLM) — the quota firewall
that makes all-sector ingestion affordable.
"""

import asyncio
import time
from dataclasses import dataclass
from datetime import UTC, datetime

import feedparser
import httpx

from common.logging import get_logger
from common.schemas import RawItemEnvelope
from ingestion.base import persist_envelopes

logger = get_logger(__name__)


@dataclass(frozen=True)
class FeedSpec:
    slug: str
    url: str
    sector: str | None = None  # set => deterministic classification, no LLM
    subsector: str | None = None


FEEDS: list[FeedSpec] = [
    # Cyber beachhead
    FeedSpec("thehackernews", "https://feeds.feedburner.com/TheHackersNews"),
    FeedSpec("bleepingcomputer", "https://www.bleepingcomputer.com/feed/"),
    # World news (general reader)
    FeedSpec("bbc_world", "http://feeds.bbci.co.uk/news/world/rss.xml"),
    FeedSpec("aljazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
    FeedSpec("guardian_world", "https://www.theguardian.com/world/rss"),
    # India (mixed feeds — LLM gate + classifier)
    FeedSpec("thehindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
    FeedSpec("timesofindia", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
    FeedSpec("ndtv", "https://feeds.feedburner.com/NDTV-LatestNews"),
    FeedSpec("hindustantimes", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"),
    # India (single-topic — deterministic, zero LLM)
    FeedSpec("livemint", "https://www.livemint.com/rss/news", sector="business"),
    FeedSpec("hindu_businessline", "https://www.thehindubusinessline.com/news/feeder/default.rss", sector="business"),
    FeedSpec("espncricinfo", "https://www.espncricinfo.com/rss/content/story/feeds/0.xml", sector="sports", subsector="cricket"),
    # Origin diversity (state affiliation labeled in seed.py)
    FeedSpec("dw", "https://rss.dw.com/rdf/rss-en-all"),
    FeedSpec("france24", "https://www.france24.com/en/rss"),
    FeedSpec("anadolu", "https://www.aa.com.tr/en/rss/default?cat=guncel"),
    FeedSpec("scmp", "https://www.scmp.com/rss/91/feed"),
    FeedSpec("dawn", "https://www.dawn.com/feeds/home"),
    FeedSpec("tass", "https://tass.com/rss/v2.xml"),
    FeedSpec("cgtn", "https://www.cgtn.com/subscribe/rss/section/world.xml"),
    FeedSpec("presstv", "https://www.presstv.ir/rss"),
]

SPEC_BY_SLUG: dict[str, FeedSpec] = {spec.slug: spec for spec in FEEDS}


async def collect() -> int:
    inserted_total = 0
    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers={"User-Agent": "prism-prototype/0.1"}) as client:
        for spec in FEEDS:
            try:
                response = await client.get(spec.url)
                response.raise_for_status()
                parsed = await asyncio.to_thread(feedparser.parse, response.text)
            except Exception:
                logger.exception("rss_fetch_failed", feed=spec.slug)
                continue

            envelopes: list[RawItemEnvelope] = []
            for entry in parsed.entries:
                external_id = entry.get("id") or entry.get("link")
                if not external_id:
                    continue
                summary = entry.get("summary", "")
                envelopes.append(
                    RawItemEnvelope(
                        source_slug=spec.slug,
                        source_type="rss",
                        external_id=external_id,
                        url=entry.get("link"),
                        title=entry.get("title", "(untitled)"),
                        body=_strip_html(summary) or None,
                        language="en",
                        published_at=_entry_datetime(entry),
                        image_url=_entry_image(entry),
                        raw={k: str(v)[:2000] for k, v in dict(entry).items()},
                    )
                )
            inserted = await persist_envelopes(envelopes)
            inserted_total += inserted
            logger.info("collector_run", collector=f"rss:{spec.slug}", new=inserted, candidates=len(envelopes))
    return inserted_total


def _entry_image(entry) -> str | None:
    """Thumbnail from RSS media extensions, before raw stringify mangles them."""
    for media in (entry.get("media_thumbnail") or []) + (entry.get("media_content") or []):
        url = media.get("url")
        if url:
            return url
    for enc in entry.get("enclosures") or []:
        if str(enc.get("type", "")).startswith("image/") and enc.get("href"):
            return enc["href"]
    return None


def _entry_datetime(entry) -> datetime | None:
    parsed = entry.get("published_parsed") or entry.get("updated_parsed")
    if not parsed:
        return None
    return datetime.fromtimestamp(time.mktime(parsed), tz=UTC)


def _strip_html(text: str) -> str:
    import re

    return re.sub(r"<[^>]+>", " ", text).strip()
