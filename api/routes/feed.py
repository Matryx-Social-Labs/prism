"""Feed route: the personalized, lens-ranked event list."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import FeedItem, FeedResponse
from common.db import get_db
from common.lenses import get_lens
from common.taxonomy import TAXONOMY

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
        items.append(build_feed_item(row, active_lens, region))
    if sort == "top":
        items.sort(key=lambda i: i.score, reverse=True)
    else:  # latest — a news feed reads newest-first by default
        items.sort(key=lambda i: i.last_updated_at, reverse=True)
    return FeedResponse(items=items[:limit], lens=active_lens.slug)
