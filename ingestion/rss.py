"""RSS collectors — professional beachheads, world news, and regional/topic feeds.

Outlet countries and state-affiliation labels are set in ingestion/seed.py;
distinct origins feed the Both-Sides perspective grouping and the
coverage-origin balance on international stories.

Feeds with a `sector` set are single-topic: their items are classified
deterministically (no gate LLM, no classifier LLM) — the quota firewall
that makes all-sector ingestion affordable.
"""

import asyncio
import calendar
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo

import feedparser
import httpx

from common.logging import get_logger
from common.schemas import RawItemEnvelope
from ingestion.base import (
    clean_text,
    get_watermark,
    persist_envelopes,
    set_watermark,
)

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
    # ── Origin feeds: the institution's own release, not an outlet's report of it.
    # Measured 2026-09-21 with this User-Agent: RBI answers 200, entries are dated
    # and carry the full release in the summary. Deterministic finance sector.
    FeedSpec("rbi", "https://www.rbi.org.in/pressreleases_rss.xml", sector="finance"),
    # PIB: the edge 403s any User-Agent that carries a URL (ours does; `Foo/1.0
    # (+example.com)` passes, `Foo/1.0 (+https://example.com)` does not), the
    # Lang=1 URL redirects to Hindi unless `reg=3` is added, and entries carry no
    # date and no body. Off until a per-feed UA and a fulltext path are measured.
    FeedSpec("pib", "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&Regid=3&reg=3", enabled=False),
    # SEBI: the feed answers 200 but the release pages 403 this User-Agent, the
    # summaries are 50–200 chars, and the feed is mostly enforcement orders and
    # recovery certificates rather than press releases. Off until a press-release
    # -only feed is found.
    FeedSpec("sebi", "https://www.sebi.gov.in/sebirss.xml", sector="finance", enabled=False),
    # ── India national — other languages (multilingual embedding clusters these
    # with the English coverage of the same story) ──
    FeedSpec("aajtak", "https://www.aajtak.in/rssfeeds/?id=home"),
    FeedSpec("amarujala", "https://www.amarujala.com/rss/breaking-news.xml"),
    FeedSpec("bbc_tamil", "https://feeds.bbci.co.uk/tamil/rss.xml"),
    # The rest of BBC's Indian-language services. Language is NOT set here — the
    # SOURCE declares it (see ingestion/base.py::persist_envelopes); a collector
    # asserting a language it cannot know is how 1,385 non-Latin articles ended
    # up labelled English.
    FeedSpec("bbc_hindi", "https://feeds.bbci.co.uk/hindi/rss.xml"),
    FeedSpec("bbc_telugu", "https://feeds.bbci.co.uk/telugu/rss.xml"),
    FeedSpec("bbc_marathi", "https://feeds.bbci.co.uk/marathi/rss.xml"),
    FeedSpec("bbc_gujarati", "https://feeds.bbci.co.uk/gujarati/rss.xml"),
    FeedSpec("bbc_punjabi", "https://feeds.bbci.co.uk/punjabi/rss.xml"),
    FeedSpec("bbc_bengali", "https://feeds.bbci.co.uk/bengali/rss.xml"),
    FeedSpec("bbc_urdu", "https://feeds.bbci.co.uk/urdu/rss.xml"),
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
RSS_CONCURRENCY = 8
IST = ZoneInfo("Asia/Kolkata")


def _conditional_headers(watermark: dict) -> dict[str, str]:
    """HTTP validators from the last successful response, never article cursors."""
    headers: dict[str, str] = {}
    if watermark.get("rss_etag"):
        headers["If-None-Match"] = str(watermark["rss_etag"])
    if watermark.get("rss_last_modified"):
        headers["If-Modified-Since"] = str(watermark["rss_last_modified"])
    return headers


def _response_watermark(current: dict, response: httpx.Response) -> dict:
    """Preserve other collector state while recording feed freshness."""
    out = dict(current)
    out.update({
        "rss_last_checked_at": datetime.now(UTC).isoformat(),
        "rss_last_status": response.status_code,
    })
    for header, key in (("etag", "rss_etag"), ("last-modified", "rss_last_modified")):
        if response.headers.get(header):
            out[key] = response.headers[header]
        elif response.status_code == 200:
            out.pop(key, None)
    if response.status_code == 200:
        out["rss_last_success_at"] = out["rss_last_checked_at"]
        out.pop("rss_last_error", None)
    return out


async def _collect_one(
    client: httpx.AsyncClient, spec: FeedSpec, semaphore: asyncio.Semaphore,
) -> int:
    async with semaphore:
        watermark: dict = {}
        try:
            watermark = await get_watermark(spec.slug)
            response = await client.get(spec.url, headers=_conditional_headers(watermark))
            if response.status_code == 304:
                await set_watermark(spec.slug, _response_watermark(watermark, response))
                logger.info("collector_not_modified", collector=f"rss:{spec.slug}")
                return 0
            response.raise_for_status()
            parsed = await asyncio.to_thread(feedparser.parse, response.text)
        except Exception as exc:
            # A feed failure is isolated from the other 26 concurrent requests.
            # Keep the last good validators and expose when/why this source failed.
            watermark = dict(watermark)
            watermark.update({
                "rss_last_checked_at": datetime.now(UTC).isoformat(),
                "rss_last_error": f"{type(exc).__name__}: {exc}"[:500],
            })
            try:
                await set_watermark(spec.slug, watermark)
            except Exception:
                logger.exception("rss_watermark_failed", feed=spec.slug)
            logger.exception("rss_fetch_failed", feed=spec.slug)
            return 0

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
                    # None, not "en" — the source is the authority (see
                    # ingestion/base.py::persist_envelopes).
                    language=None,
                    published_at=_entry_datetime(entry),
                    image_url=_entry_image(entry),
                    raw={k: str(v)[:2000] for k, v in dict(entry).items()},
                )
            )
        try:
            inserted = await persist_envelopes(envelopes)
        except Exception as exc:
            failed = dict(watermark)
            failed.update({
                "rss_last_checked_at": datetime.now(UTC).isoformat(),
                "rss_last_error": f"persist {type(exc).__name__}: {exc}"[:500],
            })
            try:
                await set_watermark(spec.slug, failed)
            except Exception:
                logger.exception("rss_watermark_failed", feed=spec.slug)
            logger.exception("rss_persist_failed", feed=spec.slug)
            return 0
        try:
            await set_watermark(spec.slug, _response_watermark(watermark, response))
        except Exception:
            # The articles are already durable and published; a telemetry write
            # must not report the collection itself as failed.
            logger.exception("rss_watermark_failed", feed=spec.slug)
        logger.info(
            "collector_run", collector=f"rss:{spec.slug}",
            new=inserted, candidates=len(envelopes),
        )
        return inserted


async def collect() -> int:
    async with httpx.AsyncClient(timeout=60, follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        semaphore = asyncio.Semaphore(RSS_CONCURRENCY)
        inserted = await asyncio.gather(*(
            _collect_one(client, spec, semaphore) for spec in FEEDS if spec.enabled
        ))
    return sum(inserted)


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
        # feedparser refuses an RFC 822 date with no zone (RBI: "Mon, 21 Sep
        # 2026 14:30:00"). Every such feed in this registry is Indian and prints
        # its wall clock, so a bare date is read as IST.
        # ponytail: one zone for all bare dates; a FeedSpec.tz if a non-IN feed ever drops its zone
        raw = entry.get("published") or entry.get("updated")
        try:
            naive = parsedate_to_datetime(raw) if raw else None
        except (TypeError, ValueError):
            naive = None
        if naive is None:
            return None
        return (naive if naive.tzinfo else naive.replace(tzinfo=IST)).astimezone(UTC)
    # feedparser's struct_time is UTC. `time.mktime` interprets it in the machine's
    # local timezone, so a worker region change silently shifts every publication
    # time; timegm is the UTC inverse the feed value requires.
    return datetime.fromtimestamp(calendar.timegm(parsed), tz=UTC)


def _strip_html(text: str) -> str:
    # One definition, shared with every other collector — this one stripped tags
    # but left `&#039;` intact, which is exactly the drift that put raw entities
    # in front of readers.
    return clean_text(text)
