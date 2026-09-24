"""Outlet identity for the reader: a short code, and where the outlet stands.

The coverage bar on every story splits its reporting by ORIGIN — English-language
national outlets, Indian-language outlets, international outlets, wire agencies —
and the monogram stack names the mastheads. Both are derived from the `sources`
table (country, language, publisher), never asserted per article, so a new feed
gets its place on the bar the moment it is registered.

Origin is the axis Prism measures coverage on instead of a left/right spectrum:
no rating body covers Indian outlets, Indian alignment is not one axis, and a
label is an opinion — country and language are facts of the source.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Short codes the reader sees inside a 26px circle. Keyed by PUBLISHER so The
# Hindu's six state feeds share one monogram. Anything unlisted gets initials.
CODES: dict[str, str] = {
    "thehindu": "TH",
    "timesofindia": "TOI",
    "ndtv": "NDTV",
    "hindustantimes": "HT",
    "livemint": "MINT",
    "hindu_businessline": "BL",
    "espncricinfo": "ESPN",
    "aajtak": "AT",
    "amarujala": "AU",
    "prajavani": "PV",
    "tv9kannada": "TV9",
    "indianexpress": "IE",
    "scroll": "SCR",
    "deccanherald": "DH",
    "deccanchronicle": "DC",
    "telanganatoday": "TT",
    "businessstandard": "BS",
    "economictimes": "ET",
    "dainikbhaskar": "DB",
    "navbharattimes": "NBT",
    "maharashtratimes": "MT",
    "sakshi": "SAK",
    "dinamani": "DIN",
    "mathrubhumi": "MB",
    "madhyamam": "MAD",
    "manoramaonline": "MM",
    "dharitri": "DHA",
    "sambad": "SAM",
    "asomiyapratidin": "AP",
    "qaumiawaz": "QA",
    "thehackernews": "THN",
    "bleepingcomputer": "BC",
    "bbc": "BBC",
    "aljazeera": "AJ",
    "anadolu": "AA",
    "cgtn": "CGTN",
    "dawn": "DAWN",
    "dw": "DW",
    "france24": "F24",
    "guardian_world": "GDN",
    "presstv": "PTV",
    "scmp": "SCMP",
    "tass": "TASS",
    "nvd": "NVD",
    "cisa_kev": "CISA",
    "gdelt": "GD",
}

ORIGINS = ("national", "intl", "regional", "wire")  # the bar's fixed slot order


# The outlet's own site, for its favicon — an identifier of the source, the way
# a byline names a paper. Keyed by publisher; unlisted publishers fall back to
# the host of their feed URL.
DOMAINS: dict[str, str] = {
    "thehindu": "thehindu.com",
    "timesofindia": "timesofindia.indiatimes.com",
    "ndtv": "ndtv.com",
    "hindustantimes": "hindustantimes.com",
    "livemint": "livemint.com",
    "hindu_businessline": "thehindubusinessline.com",
    "espncricinfo": "espncricinfo.com",
    "aajtak": "aajtak.in",
    "amarujala": "amarujala.com",
    "prajavani": "prajavani.net",
    "tv9kannada": "tv9kannada.com",
    "indianexpress": "indianexpress.com",
    # feed is served off feeds.feedburner.com; the outlet's own domain is scroll.in,
    # so this MUST be explicit — the feed-host fallback would show feedburner's icon.
    "scroll": "scroll.in",
    "deccanherald": "deccanherald.com",
    "deccanchronicle": "deccanchronicle.com",
    "telanganatoday": "telanganatoday.com",
    "businessstandard": "business-standard.com",
    "economictimes": "economictimes.indiatimes.com",
    "dainikbhaskar": "bhaskar.com",
    "navbharattimes": "navbharattimes.indiatimes.com",
    "maharashtratimes": "maharashtratimes.com",
    "sakshi": "sakshi.com",
    "dinamani": "dinamani.com",
    "mathrubhumi": "mathrubhumi.com",
    "madhyamam": "madhyamam.com",
    "manoramaonline": "manoramaonline.com",
    "dharitri": "dharitri.com",
    "sambad": "sambad.in",
    "asomiyapratidin": "asomiyapratidin.in",
    "qaumiawaz": "qaumiawaz.com",
    "thehackernews": "thehackernews.com",
    "bleepingcomputer": "bleepingcomputer.com",
    "bbc": "bbc.com",
    "aljazeera": "aljazeera.com",
    "anadolu": "aa.com.tr",
    "cgtn": "cgtn.com",
    "dawn": "dawn.com",
    "dw": "dw.com",
    "france24": "france24.com",
    "guardian_world": "theguardian.com",
    "presstv": "presstv.ir",
    "scmp": "scmp.com",
    "tass": "tass.com",
    "nvd": "nvd.nist.gov",
    "cisa_kev": "cisa.gov",
}


@dataclass(frozen=True)
class Outlet:
    slug: str
    publisher: str
    name: str
    code: str
    origin: str  # one of ORIGINS
    language: str | None
    country: str | None
    domain: str | None = None


def classify(country: str | None, language: str | None, source_type: str | None = None) -> str:
    """Where an outlet sits on the coverage bar. Facts of the source, not a rating."""
    if source_type in ("cve_feed", "advisory"):
        return "wire"
    if country == "IN":
        return "national" if (language or "en") == "en" else "regional"
    return "intl"


def _initials(name: str) -> str:
    stop = {"the", "of", "news", "&", "—", "-", "and"}
    words = [w for w in name.replace("—", " ").split() if w.lower() not in stop] or name.split()
    if len(words) == 1:
        return words[0][:3].upper()
    return "".join(w[0] for w in words[:3]).upper()


def code_for(publisher: str, name: str) -> str:
    return CODES.get(publisher) or _initials(name)


def domain_for(publisher: str, slug: str) -> str | None:
    if publisher in DOMAINS:
        return DOMAINS[publisher]
    try:  # the feed registry knows the host; import lazily to keep this module light
        from ingestion.rss import SPEC_BY_SLUG

        spec = SPEC_BY_SLUG.get(slug)
        host = urlparse(spec.url).hostname if spec else None
        return host.removeprefix("www.").removeprefix("feeds.") if host else None
    except Exception:  # noqa: BLE001 — an icon is a courtesy, never a failure
        return None


_cache: tuple[float, dict[str, Outlet]] | None = None
TTL_S = 600


async def registry(db: AsyncSession) -> dict[str, Outlet]:
    """slug → Outlet for every registered source. One query every ten minutes;
    the table has forty rows and changes when a feed is added."""
    global _cache
    now = time.monotonic()
    if _cache and now - _cache[0] < TTL_S:
        return _cache[1]
    rows = (
        await db.execute(text("SELECT slug, name, source_type, publisher, country, language FROM sources"))
    ).mappings().all()
    reg = {}
    for r in rows:
        publisher = r["publisher"] or r["slug"]
        reg[r["slug"]] = Outlet(
            slug=r["slug"],
            publisher=publisher,
            name=r["name"],
            code=code_for(publisher, r["name"]),
            origin=classify(r["country"], r["language"], r["source_type"]),
            language=r["language"],
            country=r["country"],
            domain=domain_for(publisher, r["slug"]),
        )
    _cache = (now, reg)
    return reg


def reset_cache() -> None:
    global _cache
    _cache = None


# ── The monitored set: the denominator every story's count is out of ─────────
# A story with 2 outlets means "2 of the outlets Prism reads", never "2 on the
# internet". The set is every ENABLED feed in ingestion/rss.py, counted by
# publisher (The Hindu's state feeds are one masthead), and its freshness is the
# feed watermark the collector writes on every poll.
MONITORED_TTL_S = 300  # the collector polls every 5 minutes; this is its cadence
REACHABLE_WITHIN = timedelta(hours=1)  # twelve polls without an answer is a failure
_OK_STATUSES = (200, 304)  # 304 is "nothing new", which is still an answer


@dataclass(frozen=True)
class Feed:
    slug: str
    name: str
    publisher: str
    code: str
    origin: str
    language: str | None
    state: str | None  # ISO 3166-2 when the feed is one state's desk
    sector: str | None  # set when the feed is single-topic
    domain: str | None
    official: bool  # the institution's own releases (RBI), not an outlet's reporting
    checked_at: str | None  # the collector's last poll
    ok_at: str | None  # the last poll that returned new items
    reachable: bool


@dataclass(frozen=True)
class Monitored:
    feeds: tuple[Feed, ...]
    outlets: int  # distinct publishers
    checked_at: str | None  # the most recent poll of any feed


def _reachable(watermark: dict, now: datetime) -> bool:
    try:
        checked = datetime.fromisoformat(watermark["rss_last_checked_at"])
    except (KeyError, TypeError, ValueError):
        return False
    return watermark.get("rss_last_status") in _OK_STATUSES and not watermark.get("rss_last_error") and now - checked <= REACHABLE_WITHIN


_monitored_cache: tuple[float, Monitored] | None = None


async def monitored(db: AsyncSession) -> Monitored:
    """Every enabled news feed with its last poll, cached for one poll cycle."""
    global _monitored_cache
    t = time.monotonic()
    if _monitored_cache and t - _monitored_cache[0] < MONITORED_TTL_S:
        return _monitored_cache[1]
    from ingestion.rss import FEEDS  # lazily, as domain_for does

    specs = {f.slug: f for f in FEEDS if f.enabled}
    rows = (
        await db.execute(
            text(
                """
                SELECT slug, name, source_type, publisher, country, language,
                       reliability ->> 'funding' AS funding, watermark
                FROM sources WHERE slug = ANY(:slugs) ORDER BY slug
                """
            ),
            {"slugs": list(specs)},
        )
    ).mappings().all()
    now = datetime.now(UTC)
    feeds = []
    for r in rows:
        spec, wm = specs[r["slug"]], r["watermark"] or {}
        publisher = r["publisher"] or r["slug"]
        feeds.append(
            Feed(
                slug=r["slug"],
                name=r["name"],
                publisher=publisher,
                code=code_for(publisher, r["name"]),
                origin=classify(r["country"], r["language"], r["source_type"]),
                language=r["language"],
                state=spec.state,
                sector=spec.sector,
                domain=domain_for(publisher, r["slug"]),
                official=r["funding"] == "state",
                checked_at=wm.get("rss_last_checked_at"),
                ok_at=wm.get("rss_last_success_at"),
                reachable=_reachable(wm, now),
            )
        )
    checked = [f.checked_at for f in feeds if f.checked_at]
    result = Monitored(feeds=tuple(feeds), outlets=len({f.publisher for f in feeds}), checked_at=max(checked) if checked else None)
    _monitored_cache = (t, result)
    return result


def reset_monitored_cache() -> None:
    global _monitored_cache
    _monitored_cache = None
