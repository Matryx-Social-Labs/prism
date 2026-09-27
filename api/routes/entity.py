"""An actor's page: every record Prism holds about one person, organisation or place.

The cast of a record is already extracted, deduplicated and folded to a slug
(`entities`, `event_entities`). Until now those names linked to `/search`, which
is `noindex` — so the most-linked anchors on the site pointed at a page no engine
would keep, and no topical authority accrued anywhere (audit H29).

Thin pages are a liability, not an asset: 55,214 entities existed but only ~6,000
appeared in three or more records (the floor is four since 2026-09-27, see
below). The threshold lives here (`INDEXABLE_MIN_RECORDS`)
and rides in the response, so the page can render for every entity the chips point
at while asking to be indexed only when there is a story to index.
"""

import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import EntityPage, EntityRef
from common import outlets
from common.db import get_db
from common.images import placeholders, report_photo_join
from common.lenses import get_lens

router = APIRouter()

# Below this an entity page exists but asks not to be indexed: a stub would
# spend the crawl budget the records need. Measured on prod 2026-09-22: 55,214
# entities, 5,995 with >= 3. Raised 3 -> 4 on 2026-09-27: 29 of 100 indexable
# pages had under 150 words and 28 of them were three-record actors, the kind
# Google files as "crawled - currently not indexed"; at four, 1 of 71 was thin.
INDEXABLE_MIN_RECORDS = 4
MAX_RECORDS = 60


def indexable_sql(id_column: str) -> str:
    """SQL: does this entity's page ask to be indexed? The rule get_entity and the
    sitemap apply, for the chips that link to it: 85% of crawled entity pages were
    stubs (2026-09-27), found through links that could have said nofollow. Stops
    at the floor, so a national magnet costs three index probes, not a count.

    `id_column` is a column reference ("en.id"), pasted into the SQL — never a
    value, so anything but an identifier is refused."""
    if not re.fullmatch(r"[a-z_]+(\.[a-z_]+)?", id_column):
        raise ValueError(f"not a column reference: {id_column!r}")
    return f"""(SELECT count(*) FROM (
        SELECT 1 FROM event_entities ee_i JOIN events e_i ON e_i.id = ee_i.event_id
        WHERE ee_i.entity_id = {id_column}
          AND COALESCE(jsonb_array_length(e_i.projection->'source_slugs'), 0) > 0
        LIMIT {INDEXABLE_MIN_RECORDS}) served) >= {INDEXABLE_MIN_RECORDS}"""


# The extractor's type vocabulary is open, and production carries typos and
# concatenations ("org  anization", "personrole|subjectaffected"). Map what we
# recognise to a schema.org type and let everything else be a Thing rather than
# assert something false about a person.
_SCHEMA_TYPE = {
    "person": "Person",
    "company": "Organization",
    "organization": "Organization",
    "government": "GovernmentOrganization",
    "news_agency": "NewsMediaOrganization",
    "place": "Place",
    "region": "Place",
    "country": "Country",
    "location": "Place",
    "product": "Product",
}


def schema_type(entity_type: str | None) -> str:
    return _SCHEMA_TYPE.get((entity_type or "").strip().split("|")[0].lower(), "Thing")


@router.get("/api/v1/entity/{slug}", response_model=EntityPage)
async def get_entity(
    slug: str,
    limit: int = Query(default=30, ge=1, le=MAX_RECORDS),
    lens: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> EntityPage:
    """One actor and the records it appears in, newest first."""
    entity = (
        await db.execute(
            text("SELECT id, slug, name, entity_type, aliases, qid FROM entities WHERE slug = :slug"),
            {"slug": slug},
        )
    ).mappings().first()
    if entity is None:
        raise HTTPException(status_code=404, detail="no such entity")

    total = (
        await db.execute(
            text(
                """
                SELECT count(DISTINCT ee.event_id) FROM event_entities ee
                JOIN events e ON e.id = ee.event_id
                WHERE ee.entity_id = :eid
                  AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                """
            ),
            {"eid": entity["id"]},
        )
    ).scalar_one()

    rows = (
        await db.execute(
            text(
                f"""
                SELECT e.id, e.title, e.summary, e.sector, e.subsector, e.regions,
                       img.image_url AS image_url, e.projection, e.last_updated_at,
                       e.occurred_at, img.slug AS image_source_slug
                FROM event_entities ee
                JOIN events e ON e.id = ee.event_id
                {report_photo_join("e")}
                WHERE ee.entity_id = :eid
                  AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                ORDER BY e.last_updated_at DESC
                LIMIT :limit
                """
            ),
            {"eid": entity["id"], "limit": limit, "placeholders": list(await placeholders(db))},
        )
    ).mappings().all()

    registry = await outlets.registry(db)
    active_lens = get_lens(lens)
    return EntityPage(
        entity=EntityRef(
            slug=entity["slug"],
            name=entity["name"],
            entity_type=entity["entity_type"],
            schema_type=schema_type(entity["entity_type"]),
            qid=entity["qid"],
            aliases=entity["aliases"] or [],
        ),
        record_count=total,
        indexable=total >= INDEXABLE_MIN_RECORDS,
        records=[build_feed_item(row, active_lens, None, None, registry) for row in rows],
    )


@router.get("/api/v1/sitemap/entities")
async def sitemap_entities(db: AsyncSession = Depends(get_db)):
    """The actors worth a crawl: slug and last change for every entity in at
    least INDEXABLE_MIN_RECORDS served records."""
    rows = (
        await db.execute(
            text(
                """
                SELECT en.slug, max(e.last_updated_at) AS last_updated_at,
                       count(DISTINCT e.id) AS n
                FROM entities en
                JOIN event_entities ee ON ee.entity_id = en.id
                JOIN events e ON e.id = ee.event_id
                WHERE COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                GROUP BY en.slug
                HAVING count(DISTINCT e.id) >= :floor
                ORDER BY n DESC
                LIMIT 50000
                """
            ),
            {"floor": INDEXABLE_MIN_RECORDS},
        )
    ).all()
    return {
        "entities": [
            {"slug": r[0], "last_updated_at": r[1].isoformat() if r[1] else None, "record_count": r[2]}
            for r in rows
        ]
    }
