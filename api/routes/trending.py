"""Trending stories: the persistent, shareable community layer.

GET /api/v1/trending            — scoped, ranked list for the feed block + /trending page
GET /api/v1/trending/{slug}     — a shareable story (follows merges, resolves the timeline)

Stories are produced by the reconciliation pass (correlation/trending.py); this route
only serves them. Scope filters (state, sector) mirror the feed's axes.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.db import get_db

router = APIRouter()


@router.get("/api/v1/trending")
async def trending(
    state: str | None = None,  # ISO 3166-2, e.g. IN-KA — reuses the feed's geo axis
    sector: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 50)
    rows = (
        await db.execute(
            text(
                """
                SELECT st.slug, st.label, st."cast" AS cast, st.source_count, st.velocity,
                       st.sector, st.regions,
                       jsonb_array_length(st.member_event_ids) AS developments,
                       e.title AS hero_title, e.image_url AS hero_image
                FROM stories st
                LEFT JOIN events e ON e.id = st.hero_event_id
                WHERE st.status = 'active' AND st.merged_into IS NULL
                  AND (CAST(:state AS text) IS NULL OR :state = ANY(st.regions))
                  AND (CAST(:sector AS text) IS NULL OR st.sector = :sector)
                ORDER BY st.velocity DESC, st.source_count DESC, st.last_updated_at DESC
                LIMIT :lim
                """
            ),
            {"state": state, "sector": sector, "lim": limit},
        )
    ).mappings().all()
    return {
        "stories": [
            {
                "slug": r["slug"],
                "label": r["label"],
                "cast": (r["cast"] or [])[:3],
                "source_count": r["source_count"],
                "velocity": r["velocity"],  # distinct new outlets in the last 6h
                "developments": r["developments"],
                "sector": r["sector"],
                "hero_title": r["hero_title"],
                "hero_image": r["hero_image"],
            }
            for r in rows
        ]
    }


@router.get("/api/v1/trending/{slug}")
async def trending_story(slug: str, db: AsyncSession = Depends(get_db)):
    """A shareable story. Follows a merge (`merged_into`) to the canonical story so an
    old share link keeps resolving, and returns `canonical_slug` for the client to swap
    the URL. The timeline is the live story arc (start → now)."""
    story = (
        await db.execute(
            text(
                'SELECT id, slug, label, "cast" AS cast, member_event_ids, hero_event_id, '
                "sector, source_count, velocity, status, merged_into "
                "FROM stories WHERE slug = :slug"
            ),
            {"slug": slug},
        )
    ).mappings().first()
    if story is None:
        raise HTTPException(status_code=404, detail="no such story")
    # Follow the merge chain (one hop is enough — merges always point at a canonical).
    if story["merged_into"] is not None:
        story = (
            await db.execute(
                text(
                    'SELECT id, slug, label, "cast" AS cast, member_event_ids, hero_event_id, '
                    "sector, source_count, velocity, status, merged_into "
                    "FROM stories WHERE id = :id"
                ),
                {"id": str(story["merged_into"])},
            )
        ).mappings().first()
        if story is None:
            raise HTTPException(status_code=404, detail="no such story")

    from correlation.threads import story_timeline

    timeline = {"developments": [], "cast": []}
    if story["hero_event_id"]:
        timeline = await story_timeline(uuid.UUID(str(story["hero_event_id"])))
    return {
        "slug": story["slug"],
        "canonical_slug": story["slug"],  # if != the requested slug, the client should redirect
        "label": story["label"],
        "cast": story["cast"] or [],
        "sector": story["sector"],
        "source_count": story["source_count"],
        "velocity": story["velocity"],
        "status": story["status"],
        "developments": timeline.get("developments", []),
        "timeline_cast": timeline.get("cast", []),
    }
