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
    state: str | None = None,  # ISO 3166-2 (e.g. IN-KA) — surfaces the reader's state first
    languages: str | None = None,  # comma-sep, preference order; ranks + localises (never filters)
    sort: str = "latest",
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 100)
    active_lens = get_lens(lens)
    langs = [c.strip() for c in (languages or "").split(",") if c.strip()] or None
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
        # An explicit ?sector= is the reader asking for exactly that — honour it.
        sectors = [sector]
    elif interest_pairs:
        sectors = list(interest_pairs)
    else:
        # NOT active_lens.sectors. A lens is a way of RE-READING the world, not a
        # filter that shrinks it: the cyber lens declares sectors=["cybersecurity"],
        # so this line turned the entire feed into a cybersecurity-only feed for a
        # signed-in cyber reader — no elections, no markets, no world news at all.
        #
        # The lens still shapes the feed through score_event()'s RankingWeights
        # (severity, exploited, price_impact), which is the right lever: it moves
        # relevant stories UP without making everything else disappear. Raw CVE
        # records are still gated separately by include_cve_records below.
        #
        # Same principle already settled for languages: hard-filtering a news feed
        # hides major events from the reader entirely. Rank, don't filter; leave
        # hard filters to explicit user action.
        sectors = None
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
        # is_regional reflects the state when the reader gave one (India-first
        # tiering), else the country region.
        items.append(build_feed_item(row, active_lens, state or region, langs))
    if sort == "top":
        items.sort(key=lambda i: i.score, reverse=True)
    else:  # latest — a news feed reads newest-first by default
        items.sort(key=lambda i: i.last_updated_at, reverse=True)
    # Geo tier: the reader's state first, then the rest (national). Stable sort
    # keeps the score/recency order within each band.
    if state:
        items.sort(key=lambda i: not i.is_regional)
    return FeedResponse(items=items[:limit], lens=active_lens.slug)
