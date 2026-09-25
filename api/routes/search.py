"""Search route: keyword lookup across event titles, summaries and cast."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import FeedResponse
from common import outlets
from common.db import get_db
from common.images import placeholders, report_photo_join
from common.lenses import get_lens

router = APIRouter()


@router.get("/api/v1/search", response_model=FeedResponse)
async def search(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 50)
    # Neutral lens for serialization — search spans sectors; results order by
    # recency, not lens score. No CVE-only filter here: an explicit query is
    # intent, so a searched CVE record should surface.
    active_lens = get_lens("reader")
    # Served by the GIN trigram indexes on events.title/summary (migration
    # c8a3f5d21b74) and entities.name (d4b7e2a9c1f3). Substring matching is kept
    # deliberately — switching to tsvector would change what a query MEANS
    # ("modi" would stop finding "Modinagar") and would have to pick a stemming
    # language the multilingual corpus does not have. Trigrams need a query of
    # >=3 characters to use the index, so a 2-character search still scans; that
    # is the documented floor, not an oversight.
    #
    # The cast is searched as well as the words. The search page offers the
    # names in the news now — the cast of the trending stories — and a name like
    # "Nanavati Hospital" sits in a record's cast without being in its headline
    # or summary: 4 of the 6 names offered on 2026-09-25 returned nothing.
    pattern = f"%{q.strip()}%"
    rows = (
        await db.execute(
            text(
                f"""
                SELECT e.id, e.title, e.summary, e.sector, e.subsector, e.regions,
                       img.image_url AS image_url, img.slug AS image_source_slug,
                       e.projection, e.last_updated_at, e.occurred_at
                FROM events e
                {report_photo_join("e")}
                WHERE e.title ILIKE :q OR e.summary ILIKE :q
                   OR e.id IN (
                       SELECT ee.event_id FROM event_entities ee
                       JOIN entities ent ON ent.id = ee.entity_id
                       WHERE ent.name ILIKE :q
                   )
                ORDER BY e.last_updated_at DESC
                LIMIT :limit
                """
            ),
            {"q": pattern, "limit": limit, "placeholders": list(await placeholders(db))},
        )
    ).mappings().all()
    reg = await outlets.registry(db)
    items = [build_feed_item(row, active_lens, None, registry=reg) for row in rows]
    return FeedResponse(items=items, lens=active_lens.slug)
