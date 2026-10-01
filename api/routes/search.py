"""Search route: keyword lookup across event titles, summaries and cast, with
the matches that share a story collapsed under it."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import SearchResponse, SearchStoryOut
from common import outlets
from common.db import get_db
from common.images import placeholders, report_photo_join
from common.lenses import get_lens
from common.stories import STORY_BOUNDARY_STATUS

router = APIRouter()

# Two matches in one story make a group; a lone match stays a row of its own.
SEARCH_GROUP_MIN = 2


@router.get("/api/v1/search", response_model=SearchResponse)
async def search(
    q: str = Query(..., min_length=2, max_length=100),
    limit: int = 30,
    db: AsyncSession = Depends(get_db),
):
    limit = min(max(limit, 1), 50)
    # Neutral lens for serialization — search spans sectors; results order by
    # where the query matched, then recency, never lens score. No CVE-only filter here: an explicit query is
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
                SELECT e.id, e.title, e.summary, e.sector, e.subsector, e.subject_path, e.regions,
                       img.image_url AS image_url, img.slug AS image_source_slug,
                       e.projection, e.last_updated_at, e.occurred_at,
                       COALESCE(e.first_published_at, e.first_seen_at) AS first_published_at
                FROM events e
                {report_photo_join("e")}
                WHERE (e.title ILIKE :q OR e.summary ILIKE :q
                   OR e.id IN (
                       SELECT ee.event_id FROM event_entities ee
                       JOIN entities ent ON ent.id = ee.entity_id
                       WHERE ent.name ILIKE :q
                   ))
                  AND e.merged_into IS NULL
                  AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                -- The record the query NAMES leads: a title match outranks a
                -- fresher record that only mentions it in its summary or cast
                -- ("Sun Pharma" sank below the day's market wraps, audit
                -- 2026-09-27 P0 #7). Recency orders within each tier.
                ORDER BY (e.title ILIKE :q) DESC, e.last_updated_at DESC
                LIMIT :limit
                """
            ),
            {"q": pattern, "limit": limit, "placeholders": list(await placeholders(db))},
        )
    ).mappings().all()
    reg = await outlets.registry(db)
    items = [build_feed_item(row, active_lens, None, registry=reg) for row in rows]
    return SearchResponse(items=items, lens=active_lens.slug, stories=await _story_groups(db, rows))


async def _story_groups(db: AsyncSession, rows) -> list[SearchStoryOut]:
    """The stories two or more matches belong to, each with its matches in the
    order they were first reported; groups in the order of their best match.

    A record's story is resolved as the record page resolves it
    (api/routes/events.get_event): the newest unmerged story whose frozen member
    set holds it. One pass over the unmerged stories' members (343 stories,
    ~8k members on 2026-10-01), not a containment scan per match."""
    if not rows:
        return []
    owners = (
        await db.execute(
            text(
                """
                SELECT DISTINCT ON (m.event_id) m.event_id, st.slug, st.label,
                       jsonb_array_length(st.member_event_ids) AS developments,
                       (SELECT max(COALESCE(e.first_published_at, e.first_seen_at)) FROM events e
                        WHERE e.id IN (SELECT CAST(x AS uuid) FROM jsonb_array_elements_text(st.member_event_ids) x)
                       ) AS latest
                FROM stories st
                CROSS JOIN LATERAL jsonb_array_elements_text(st.member_event_ids) AS m(event_id)
                WHERE st.merged_into IS NULL AND m.event_id = ANY(CAST(:ids AS text[]))
                ORDER BY m.event_id, st.last_updated_at DESC
                """
            ),
            {"ids": [str(r["id"]) for r in rows]},
        )
    ).mappings().all()
    story_of = {o["event_id"]: o for o in owners}
    members: dict[str, list] = {}
    for r in rows:  # search order, so the first group seen holds the best match
        if (o := story_of.get(str(r["id"]))) is not None:
            members.setdefault(o["slug"], []).append(r)
    groups = []
    for slug, matched in members.items():
        if len(matched) < SEARCH_GROUP_MIN:
            continue
        o = story_of[str(matched[0]["id"])]
        groups.append(
            SearchStoryOut(
                slug=slug,
                label=o["label"],
                developments=o["developments"],
                latest_published_at=o["latest"].isoformat() if o["latest"] else None,
                event_ids=[str(r["id"]) for r in sorted(matched, key=lambda r: (r["first_published_at"], str(r["id"])))],
                boundary_status=STORY_BOUNDARY_STATUS,
            )
        )
    return groups
