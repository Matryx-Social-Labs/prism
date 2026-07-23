"""Shared row → FeedItem serialization for the feed and search routes.

Pure serialization: curation rules (CVE-only records, subsector narrowing) stay
in the feed route since they're feed-specific; search wants every match.
"""

from datetime import UTC, datetime
from typing import Any

from api.schemas import FeedItem
from common.lenses import Lens
from personalization.ranking import score_event


def _pick_headline(
    projection: dict, default: str, languages: list[str] | None
) -> tuple[str, str | None]:
    """Render the event's headline in the reader's preferred language, falling back
    to English then the event title. Returns (title, headline_lang) — the frontend
    shows a mono language tag when headline_lang isn't the reader's primary."""
    if not languages:
        return default, None
    by_lang = {h["lang"]: h for h in (projection.get("headlines") or []) if h.get("title")}
    for pref in languages:
        if pref in by_lang:
            return by_lang[pref]["title"], pref
    if "en" in by_lang:  # visible English fallback (never hide the story)
        return by_lang["en"]["title"], "en"
    return default, None


def build_feed_item(
    row: Any, active_lens: Lens, region: str | None, languages: list[str] | None = None
) -> FeedItem:
    projection = row["projection"] or {}
    cyber = projection.get("cyber") or {}
    finance = projection.get("finance") or {}
    cvss = cyber.get("cvss") or {}
    kev = bool((cyber.get("exploitation") or {}).get("kev_listed"))
    # Recency = when the event happened, not when we ingested it — otherwise a
    # backfill makes years-old records look breaking.
    occurred = row["occurred_at"]
    reference_time = (
        datetime.combine(occurred, datetime.min.time(), tzinfo=UTC) if occurred else row["last_updated_at"]
    )
    score = score_event(
        lens=active_lens, reference_time=reference_time, projection=projection, languages=languages
    )
    title, headline_lang = _pick_headline(projection, row["title"], languages)
    return FeedItem(
        id=str(row["id"]),
        title=title,
        headline_lang=headline_lang,
        available_languages=projection.get("languages") or [],
        summary=row["summary"],
        sector=row["sector"],
        subsector=row["subsector"],
        regions=row["regions"] or [],
        image_url=row["image_url"],
        is_regional=bool(region and region in (row["regions"] or [])),
        coverage=projection.get("coverage"),
        event_type=projection.get("event_type"),
        source_count=projection.get("source_count", 1),
        cvss_score=cvss.get("score"),
        cvss_severity=cvss.get("severity"),
        kev_listed=kev,
        cve_ids=(cyber.get("cve_ids") or [])[:4],
        tickers=(finance.get("tickers") or [])[:4],
        catalyst=finance.get("catalyst"),
        price_impact_direction=(finance.get("price_impact") or {}).get("direction"),
        last_updated_at=row["last_updated_at"].isoformat(),
        score=score,
    )
