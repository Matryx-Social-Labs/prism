"""Feed route: the personalized, lens-ranked event list."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import FeedItem, FeedResponse
from common.db import get_db
from common.lenses import get_lens
from common.taxonomy import TAXONOMY
from personalization.ranking import score_event

router = APIRouter()


@router.get("/api/v1/feed", response_model=FeedResponse)
async def get_feed(
    lens: str | None = None,
    sector: str | None = None,
    interests: str | None = None,
    region: str | None = None,
    sort: str = "latest",
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    active_lens = get_lens(lens)
    # Interest pairs from the profile: "sports:cricket,politics,technology:ai".
    # A bare sector means the whole sector; explicit ?sector= wins over both.
    interest_pairs: dict[str, set[str]] = {}
    for token in (interests or "").split(","):
        token = token.strip()
        if not token:
            continue
        sec, _, sub = token.partition(":")
        if sec not in TAXONOMY:
            continue
        interest_pairs.setdefault(sec, set())
        if sub and sub in TAXONOMY[sec]:
            interest_pairs[sec].add(sub)
    if sector:
        sectors = [sector]
    elif interest_pairs:
        sectors = list(interest_pairs)
    else:
        sectors = active_lens.sectors
    # Candidate window is per-sector so a high-churn sector (thousands of
    # CVE updates a day) can't evict everyone else's news before ranking.
    rows = (
        await db.execute(
            text(
                """
                SELECT id, title, summary, sector, subsector, regions, image_url,
                       projection, last_updated_at, occurred_at
                FROM (
                    SELECT e.*, ROW_NUMBER() OVER (
                        PARTITION BY e.sector ORDER BY e.last_updated_at DESC
                    ) AS rn
                    FROM events e
                    WHERE (CAST(:sectors AS text[]) IS NULL
                           OR e.sector = ANY(CAST(:sectors AS text[])))
                ) windowed
                WHERE rn <= 120
                """
            ),
            {"sectors": sectors or None},
        )
    ).mappings().all()

    cve_only_sources = {"nvd", "cisa_kev"}
    items: list[FeedItem] = []
    for row in rows:
        projection = row["projection"] or {}
        # Raw database records (no news coverage) only surface for lenses
        # that want them (cyber/GRC); they're noise for readers and traders.
        slugs = set(projection.get("source_slugs") or [])
        if slugs and slugs <= cve_only_sources and not active_lens.include_cve_records:
            continue
        # Subsector narrowing: an interest like sports:cricket drops other
        # subsectors of that sector (unclassified subsectors stay visible
        # only when the whole sector was selected).
        wanted_subs = interest_pairs.get(row["sector"] or "")
        if wanted_subs and row["subsector"] not in wanted_subs:
            continue
        cyber = projection.get("cyber") or {}
        finance = projection.get("finance") or {}
        cvss = cyber.get("cvss") or {}
        kev = bool((cyber.get("exploitation") or {}).get("kev_listed"))
        # Recency = when the event happened, not when we ingested it —
        # otherwise a backfill makes years-old records look breaking.
        occurred = row["occurred_at"]
        reference_time = (
            datetime.combine(occurred, datetime.min.time(), tzinfo=UTC)
            if occurred
            else row["last_updated_at"]
        )
        score = score_event(
            lens=active_lens,
            reference_time=reference_time,
            projection=projection,
        )
        items.append(
            FeedItem(
                id=str(row["id"]),
                title=row["title"],
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
        )
    if sort == "top":
        items.sort(key=lambda i: i.score, reverse=True)
    else:  # latest — a news feed reads newest-first by default
        items.sort(key=lambda i: i.last_updated_at, reverse=True)
    return FeedResponse(items=items[:limit], lens=active_lens.slug)
