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

from api.schemas import TrendingResponse, TrendingStoryDetail
from common.db import get_db
from common.taxonomy import TAXONOMY

router = APIRouter()

# Chains observed in production are 1-2 hops; this is a corruption guard, not a limit.
_MAX_MERGE_HOPS = 8


@router.get("/api/v1/trending", response_model=TrendingResponse)
async def trending(
    state: str | None = None,  # ISO 3166-2, e.g. IN-KA — reuses the feed's geo axis
    sector: str | None = None,
    limit: int = 20,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 50)
    # Comma-separated like the feed's: the reader's six subjects are groups of
    # the pipeline's ten (Business & Markets is business+finance). Unknown names
    # are dropped rather than 400'd; an all-unknown list matches nothing.
    sectors = None
    if sector:
        sectors = [x for x in (t.strip() for t in sector.split(",")) if x in TAXONOMY] or [sector]
    rows = (
        await db.execute(
            text(
                """
                SELECT st.slug, st.label, st."cast" AS cast, st.source_count, st.velocity,
                       st.sector, st.regions, st.hero_event_id, st.member_event_ids,
                       st.first_seen_at, st.last_updated_at,
                       jsonb_array_length(st.member_event_ids) AS developments,
                       e.title AS hero_title, e.image_url AS hero_image
                FROM stories st
                LEFT JOIN events e ON e.id = st.hero_event_id
                WHERE st.status = 'active' AND st.merged_into IS NULL
                  AND (CAST(:state AS text) IS NULL OR :state = ANY(st.regions))
                  AND (CAST(:sectors AS text[]) IS NULL OR st.sector = ANY(:sectors))
                ORDER BY st.velocity DESC, st.source_count DESC, st.last_updated_at DESC
                LIMIT :lim
                """
            ),
            {"state": state, "sectors": sectors, "lim": limit},
        )
    ).mappings().all()
    routes = [await _route_for(db, r["member_event_ids"]) for r in rows]
    return {
        "stories": [
            {
                "route": route,
                "slug": r["slug"],
                "label": r["label"],
                "cast": (r["cast"] or [])[:3],
                "source_count": r["source_count"],
                "velocity": r["velocity"],  # distinct new outlets in the last 6h
                "developments": r["developments"],
                "sector": r["sector"],
                "hero_title": r["hero_title"],
                "hero_image": r["hero_image"],
                # The chart of arcs prints LAST MOVED and SPAN, and a row opens
                # the ticket of the story's hero event with the route in view.
                "hero_event_id": str(r["hero_event_id"]) if r["hero_event_id"] else None,
                "first_seen_at": r["first_seen_at"].isoformat() if r["first_seen_at"] else None,
                "last_updated_at": r["last_updated_at"].isoformat() if r["last_updated_at"] else None,
            }
            for r, route in zip(rows, routes, strict=True)
        ]
    }


async def _route_for(db: AsyncSession, member_ids: list | None) -> dict | None:
    """The route glyph's data for one row: the persisted branch tree, each node
    with the day it happened. One small query per row on a list of at most 50."""
    from correlation.threads import branch_tree_for_members

    tree = await branch_tree_for_members(member_ids)
    if not tree:
        return None
    days = (
        await db.execute(
            text("SELECT id::text AS id, occurred_at FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [n["id"] for n in tree["nodes"]]},
        )
    ).mappings().all()
    when = {d["id"]: d["occurred_at"].isoformat() if d["occurred_at"] else None for d in days}
    return {
        "root_id": tree["root_id"],
        "nodes": [{"id": n["id"], "parent_id": n["parent_id"], "off_spine": n["off_spine"], "occurred_at": when.get(n["id"])} for n in tree["nodes"]],
    }


@router.get("/api/v1/trending/{slug}", response_model=TrendingStoryDetail)
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
    # Follow the merge chain to its end.
    #
    # This used to take exactly one hop, on the stated assumption that "merges
    # always point at a canonical". Production disagrees: an audit on 2026-07-28
    # found a two-hop chain among 356 merged rows. One hop lands on a story that
    # is ITSELF merged — dormant, superseded, not what the reader should see —
    # so that share link silently resolved to a dead story instead of the live one.
    #
    # Bounded rather than `while`: a cycle would hang the request thread, and a
    # chain longer than this is corruption worth failing loudly on.
    seen: set[str] = set()
    for _ in range(_MAX_MERGE_HOPS):
        if story["merged_into"] is None:
            break
        nxt = str(story["merged_into"])
        if nxt in seen:
            raise HTTPException(status_code=500, detail="merge cycle")
        seen.add(nxt)
        story = (
            await db.execute(
                text(
                    'SELECT id, slug, label, "cast" AS cast, member_event_ids, hero_event_id, '
                    "sector, source_count, velocity, status, merged_into "
                    "FROM stories WHERE id = :id"
                ),
                {"id": nxt},
            )
        ).mappings().first()
        if story is None:
            raise HTTPException(status_code=404, detail="no such story")
    else:
        if story["merged_into"] is not None:
            raise HTTPException(status_code=500, detail="merge chain too deep")

    from correlation.threads import branch_tree_for_members, story_timeline_from_members

    timeline = {"developments": [], "cast": []}
    branches = None
    if story["hero_event_id"]:
        # Pin the share view to the member set this slug EARNED, not the live global
        # partition — a shared link keeps its identity as coverage/boundaries shift.
        timeline = await story_timeline_from_members(
            uuid.UUID(str(story["hero_event_id"])), story["member_event_ids"]
        )
        # The L3 branch tree for the SAME frozen member set. None when the story
        # predates the current partition run — the client falls back to the flat
        # timeline it already renders, so this is additive with no regression.
        branches = await branch_tree_for_members(story["member_event_ids"])
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
        "branches": branches,
    }
