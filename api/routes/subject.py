"""The subject tree as the reader meets it: a nav, a node, and its stories.

A node is a URL and a feed or it should not exist (`common/subjects.py`). This
is the half that makes that true: `/api/v1/subjects` is the tree the nav
renders, and `/api/v1/subject/{path}` is one node with the stories under it —
under IT, not under its exact path, so `civic.crime` returns the violent, the
property and the unsplit ones together. That prefix query is the whole reason
the path is a dotted string with a `text_pattern_ops` index.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import SubjectNode, SubjectPage, SubjectTree
from common import outlets, subjects
from common.db import get_db
from common.images import placeholder_hashes
from common.lenses import get_lens

router = APIRouter()

MAX_STORIES = 60


def _node(path: str, count: int | None = None) -> SubjectNode:
    s = subjects.get(path)
    return SubjectNode(
        path=s.path, slug=s.path.rsplit(".", 1)[-1], label=s.label,
        depth=subjects.depth(s.path), story_count=count,
    )


@router.get("/api/v1/subjects", response_model=SubjectTree)
async def get_subjects(db: AsyncSession = Depends(get_db)) -> SubjectTree:
    """Every node, with how many served stories sit under it in the live window.

    The count is LIVENESS — stories in the last 30 days — which is what the nav
    needs to avoid offering a reader a room nobody has been in this month. A
    node's own page counts its whole archive instead; the two numbers answer
    different questions and are deliberately not the same."""
    rows = (
        await db.execute(
            text(
                """
                SELECT subject_path, count(*) AS n FROM events
                WHERE subject_path IS NOT NULL
                  AND COALESCE(jsonb_array_length(projection->'source_slugs'), 0) > 0
                  AND last_updated_at > now() - interval '30 days'
                GROUP BY subject_path
                """
            )
        )
    ).all()
    # A story on a leaf counts for every ancestor: `civic` holds what
    # `civic.crime.violent` holds.
    counts: dict[str, int] = {}
    for path, n in rows:
        parts = path.split(".")
        for i in range(1, len(parts) + 1):
            counts[".".join(parts[:i])] = counts.get(".".join(parts[:i]), 0) + n
    return SubjectTree(
        roots=[_node(p, counts.get(p, 0)) for p in subjects.ROOTS],
        nodes=[_node(s.path, counts.get(s.path, 0)) for s in subjects.SUBJECTS],
    )


@router.get("/api/v1/subject/{path:path}", response_model=SubjectPage)
async def get_subject(
    path: str,
    limit: int = Query(default=30, ge=1, le=MAX_STORIES),
    lens: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> SubjectPage:
    """One node, its ancestors, its children, and the stories under it."""
    path = path.strip("/").replace("/", ".")
    if not subjects.is_valid(path):
        raise HTTPException(status_code=404, detail="no such subject")

    rows = (
        await db.execute(
            text(
                """
                SELECT e.id, e.title, e.summary, e.sector, e.subsector, e.regions,
                       img.image_url AS image_url, e.projection, e.last_updated_at,
                       e.occurred_at, img.slug AS image_source_slug
                FROM events e
                LEFT JOIN LATERAL (
                    SELECT ri.image_url, s.slug FROM event_memberships m
                    JOIN articles a ON a.id = m.article_id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    JOIN sources s ON s.id = ri.source_id
                    WHERE m.event_id = e.id AND ri.image_url IS NOT NULL
                      AND (ri.image_phash IS NULL OR NOT (ri.image_phash = ANY(CAST(:placeholders AS text[]))))
                    ORDER BY (ri.image_url = e.image_url) DESC, ri.published_at ASC NULLS LAST
                    LIMIT 1
                ) img ON true
                -- The node AND everything under it: `civic.crime` is the violent,
                -- the property and the ones we could not split.
                WHERE (e.subject_path = :path OR e.subject_path LIKE :prefix)
                  AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                ORDER BY e.last_updated_at DESC
                LIMIT :limit
                """
            ),
            {"path": path, "prefix": f"{path}.%", "limit": limit,
             "placeholders": list(await placeholder_hashes(db))},
        )
    ).mappings().all()

    total = (
        await db.execute(
            text(
                """
                -- No window: this counts what the page LISTS, and the page lists
                -- the archive newest first. The tree's own counts are windowed
                -- because they answer a different question (is this node alive
                -- now), and a page that said "0 stories" above two stories is
                -- the bug that taught us to keep the two apart.
                SELECT count(*) FROM events
                WHERE (subject_path = :path OR subject_path LIKE :prefix)
                  AND COALESCE(jsonb_array_length(projection->'source_slugs'), 0) > 0
                """
            ),
            {"path": path, "prefix": f"{path}.%"},
        )
    ).scalar_one()

    registry = await outlets.registry(db)
    active_lens = get_lens(lens)
    parts = path.split(".")
    return SubjectPage(
        node=_node(path, total),
        ancestors=[_node(".".join(parts[:i])) for i in range(1, len(parts))],
        children=[_node(c.path) for c in subjects.children(path)],
        story_count=total,
        stories=[build_feed_item(row, active_lens, None, None, registry) for row in rows],
    )
