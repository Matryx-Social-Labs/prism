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
from ingestion.base import clean_text, persist_envelopes

logger = get_logger(__name__)


@dataclass(frozen=True)
class FeedSpec:
    slug: str
    url: str
    sector: str | None = None  # set => deterministic classification, no LLM
    subsector: str | None = None
    state: str | None = None  # ISO 3166-2 (e.g. IN-KA) => stamped on the event's regions
    # Kept in the list rather than deleted when a feed goes dark, so the reason
    # survives and re-enabling is a one-word change.
    enabled: bool = True


# India-first scope: national + state general news, plus the cyber lens beachhead.
# International general news is intentionally out for now (start focused on India,
# scale geography vertically later). State feeds carry an ISO 3166-2 code so the
# feed can tier local(state) -> national.
FEEDS: list[FeedSpec] = [
    # ── India national (general — LLM gate + classifier) ──
    FeedSpec("thehindu", "https://www.thehindu.com/news/national/feeder/default.rss"),
    FeedSpec("timesofindia", "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
    FeedSpec("ndtv", "https://feeds.feedburner.com/NDTV-LatestNews"),
    FeedSpec("hindustantimes", "https://www.hindustantimes.com/feeds/rss/india-news/rssfeed.xml"),
    # ── India national (single-topic — deterministic, zero LLM) ──
    FeedSpec("livemint", "https://www.livemint.com/rss/news", sector="business"),
    FeedSpec("hindu_businessline", "https://www.thehindubusinessline.com/news/feeder/default.rss", sector="business"),
    FeedSpec("espncricinfo", "https://www.espncricinfo.com/rss/content/story/feeds/0.xml", sector="sports", subsector="cricket"),
    # ── India national — other languages (multilingual embedding clusters these
    # with the English coverage of the same story) ──
    FeedSpec("aajtak", "https://www.aajtak.in/rssfeeds/?id=home"),
    FeedSpec("amarujala", "https://www.amarujala.com/rss/breaking-news.xml"),
    FeedSpec("bbc_tamil", "https://feeds.bbci.co.uk/tamil/rss.xml"),
    # Kannada (Bangalore launch). Validated: 5/5 Kannada titles, fresh dailies.
    FeedSpec("prajavani", "https://www.prajavani.net/feed", state="IN-KA"),
    FeedSpec("tv9kannada", "https://tv9kannada.com/feed", state="IN-KA"),
    # ── India state editions (The Hindu state feeds + TOI metros) ──
    FeedSpec("thehindu_tamilnadu", "https://www.thehindu.com/news/national/tamil-nadu/feeder/default.rss", state="IN-TN"),
    FeedSpec("thehindu_kerala", "https://www.thehindu.com/news/national/kerala/feeder/default.rss", state="IN-KL"),
    FeedSpec("thehindu_karnataka", "https://www.thehindu.com/news/national/karnataka/feeder/default.rss", state="IN-KA"),
    FeedSpec("thehindu_andhra", "https://www.thehindu.com/news/national/andhra-pradesh/feeder/default.rss", state="IN-AP"),
    FeedSpec("thehindu_telangana", "https://www.thehindu.com/news/national/telangana/feeder/default.rss", state="IN-TG"),
    FeedSpec("toi_delhi", "https://timesofindia.indiatimes.com/rssfeeds/-2128839596.cms", state="IN-DL"),
    FeedSpec("toi_mumbai", "https://timesofindia.indiatimes.com/rssfeeds/-2128838597.cms", state="IN-MH"),
    # ── Cybersecurity lens (global by nature — feeds the cyber lens, not the India general feed) ──
    FeedSpec("thehackernews", "https://feeds.feedburner.com/TheHackersNews"),
    # 403 on EVERY 30-minute cycle since ingestion began — a dead collector
    # emitting a traceback per cycle. The block is on the egress IP, not on us:
    # measured 2026-07-29, the feed returns 200 to this exact User-Agent from a
    # residential address and 403 from Railway. So there is no UA to fix, and
    # spoofing a browser to get around a datacentre-IP rule would be evading a
    # deliberate block rather than fixing a bug. Off until the egress changes.
    FeedSpec("bleepingcomputer", "https://www.bleepingcomputer.com/feed/", enabled=False),
]

# Identify honestly and be reachable: the old "prism-prototype/0.1" named no
# product, offered no contact, and told every publisher we were a toy.
USER_AGENT = "Prism/1.0 (+https://www.readprism.news)"

SPEC_BY_SLUG: dict[str, FeedSpec] = {spec.slug: spec for spec in FEEDS}


async def collect() -> int:
    inserted_total = 0
    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        for spec in FEEDS:
            if not spec.enabled:
                continue
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
    # One definition, shared with every other collector — this one stripped tags
    # but left `&#039;` intact, which is exactly the drift that put raw entities
    # in front of readers.
    return clean_text(text)
