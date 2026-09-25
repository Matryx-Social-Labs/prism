"""Digest route: the synthesized Market Pulse (cached, generated on demand)."""

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import DigestResponse
from common import outlets
from common.db import get_db
from common.images import placeholders, report_photo_join
from common.lenses import get_lens
from correlation.digest import get_market_digest

router = APIRouter()


@router.get("/api/v1/digest/markets", response_model=DigestResponse)
async def market_digest(db: AsyncSession = Depends(get_db)):
    digest = await get_market_digest()
    if digest is None:  # synthesis unavailable (e.g. LLM quota) — hide, don't 500
        return Response(status_code=204)
    # The stories the digest was written from, as chart rows: the page shows
    # the record under the reading, not a verdict on its own. In the digest's
    # order, which is the order the synthesis considered them.
    ids = [str(x) for x in (digest.get("event_ids") or [])][:24]
    stories = []
    if ids:
        rows = (
            await db.execute(
                text(
                    f"""
                    SELECT e.id, e.title, e.summary, e.sector, e.subsector, e.regions,
                           img.image_url AS image_url, img.slug AS image_source_slug,
                           e.projection, e.last_updated_at, e.occurred_at
                    FROM events e
                    {report_photo_join("e")}
                    WHERE e.id = ANY(CAST(:ids AS uuid[]))
                    """
                ),
                {"ids": ids, "placeholders": list(await placeholders(db))},
            )
        ).mappings().all()
        by_id = {str(r["id"]): r for r in rows}
        lens = get_lens("markets")
        reg = await outlets.registry(db)
        stories = [build_feed_item(by_id[i], lens, None, registry=reg) for i in ids if i in by_id]
    return DigestResponse(**digest, stories=stories)
