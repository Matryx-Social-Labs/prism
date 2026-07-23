"""Search route: keyword lookup across event titles and summaries."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import FeedResponse
from common.db import get_db
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
    pattern = f"%{q.strip()}%"  # ponytail: ILIKE full-scan; add pg_trgm/tsvector index if the corpus grows
    rows = (
        await db.execute(
            text(
                """
                SELECT id, title, summary, sector, subsector, regions, image_url,
                       projection, last_updated_at, occurred_at
                FROM events
                WHERE title ILIKE :q OR summary ILIKE :q
                ORDER BY last_updated_at DESC
                LIMIT :limit
                """
            ),
            {"q": pattern, "limit": limit},
        )
    ).mappings().all()
    items = [build_feed_item(row, active_lens, None) for row in rows]
    return FeedResponse(items=items, lens=active_lens.slug)
