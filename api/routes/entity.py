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
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.routes.serialization import build_feed_item
from api.schemas import EntityPage, EntityQuote, EntityRef
from common import outlets
from common.db import get_db
from common.images import placeholders, report_photo_join
from common.lenses import get_lens
from common.regions import HUB_SLUGS
from enrichment.claims import dedupe_sources, speaker_key

router = APIRouter()

# Below this an entity page exists but asks not to be indexed: a stub would
# spend the crawl budget the records need. Measured on prod 2026-09-22: 55,214
# entities, 5,995 with >= 3. Raised 3 -> 4 on 2026-09-27: 29 of 100 indexable
# pages had under 150 words and 28 of them were three-record actors, the kind
# Google files as "crawled - currently not indexed"; at four, 1 of 71 was thin.
INDEXABLE_MIN_RECORDS = 4
MAX_RECORDS = 60
ENTITY_CACHE = "public, s-maxage=300, stale-while-revalidate=900"
# "What <name> said": at most this many quotes, read from the newest MAX_RECORDS
# records. Every quote is re-checked against its article's text on the way out.
MAX_QUOTES = 20


def speaker_fold(name: str) -> str:
    """speaker_key with the spaces taken out: "D.K. Shivakumar", "D K Shivakumar"
    and "DK Shivakumar" are one string."""
    return speaker_key(name).replace(" ", "")


def speaker_keys(name: str, aliases: Sequence[str] | None) -> set[str]:
    """The folded strings a speaker must equal IN FULL to be this entity: its name
    and its aliases. A one-word alias of a longer name is a surname or a first
    name ("Reddy", "Modi"), which names nobody in particular (two different
    Reddys: enrichment/claims.speaker_key), so it never counts."""
    one_word = len(speaker_key(name).split()) == 1
    keys = {speaker_fold(name)} | {
        speaker_fold(a) for a in aliases or []
        if isinstance(a, str) and (one_word or len(speaker_key(a).split()) > 1)
    }
    return keys - {""}


def entity_quotes(
    records: Sequence[tuple[str, str, Sequence[Mapping[str, Any]]]],
    keys: set[str],
    verdicts: Mapping[str, dict[str, dict]] | None = None,
) -> tuple[list[EntityQuote], str | None]:
    """Every quote the story pages print for this entity, newest first and once
    each, and the role its records give it most often.

    `records` is (event id, title, ALL the record's article rows newest first),
    newest record first. All of them, not only the speaker's: the story page
    settles a quote two speakers were given, and folds "Shivakumar" into
    "D.K. Shivakumar", across the whole record. The checks are group_claims's,
    the story page's own, so this page cannot print a quote its record would not.
    """
    from api.routes.events import group_claims  # events imports indexable_sql from here

    out: list[EntityQuote] = []
    seen: set[str] = set()
    roles: Counter[str] = Counter()
    for event_id, title, rows in records:
        sources = dedupe_sources(list(rows))
        index = {str(s["article_id"]): n for n, s in enumerate(sources, 1)}  # the record's [n]
        for group in group_claims(sources, (verdicts or {}).get(event_id)):
            if speaker_fold(group.speaker) not in keys:
                continue
            if group.role:
                roles[group.role] += 1
            for c in group.claims:
                if c.id in seen:  # the same words on two records are one quote
                    continue
                seen.add(c.id)
                out.append(EntityQuote.model_validate(
                    {**c.model_dump(), "event_id": event_id, "event_title": title,
                     "source_index": index.get(c.article_id)}
                ))
    out.sort(key=lambda q: q.published_at or "", reverse=True)
    return out, roles.most_common(1)[0][0] if roles else None


# The story page's article rows (api/routes/events.get_event), for each of the
# entity's newest records whose stored claims name it. The speaker test here is
# only a pre-filter (Postgres lower() is not Python's casefold): entity_quotes
# decides, and a speaker the filter misses loses a quote, never gains one.
_QUOTED_RECORD_SOURCES = text(
    """
    WITH recent AS MATERIALIZED (
        SELECT e.id, e.title, e.last_updated_at
        FROM event_entities ee JOIN events e ON e.id = ee.event_id
        WHERE ee.entity_id = :eid
          AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
        ORDER BY e.last_updated_at DESC
        LIMIT :window
    ), said AS MATERIALIZED (
        SELECT r.id AS event_id, r.title, r.last_updated_at, em.article_id,
               CASE WHEN jsonb_typeof(en.shared_fields -> 'claims') = 'array'
                    THEN en.shared_fields -> 'claims' END AS claims
        FROM recent r
        JOIN event_memberships em ON em.event_id = r.id
        LEFT JOIN enrichments en ON en.article_id = em.article_id
    ), quoted AS (
        SELECT DISTINCT s.event_id FROM said s, jsonb_array_elements(COALESCE(s.claims, '[]'::jsonb)) c
        WHERE lower(regexp_replace(c ->> 'speaker', '[.\\s]+', '', 'g')) = ANY(:keys)
    )
    SELECT s.event_id, s.title AS event_title,
           a.id AS article_id, src.name AS source_name, ri.url, ri.url_canonical,
           ri.published_at, ri.language AS lang, s.claims,
           CASE WHEN jsonb_array_length(s.claims) > 0 THEN a.clean_text END AS clean_text
    FROM said s
    JOIN quoted q ON q.event_id = s.event_id
    JOIN articles a ON a.id = s.article_id
    JOIN raw_items ri ON ri.id = a.raw_item_id
    JOIN sources src ON src.id = ri.source_id
    ORDER BY s.last_updated_at DESC, s.event_id, ri.published_at DESC NULLS LAST, a.id
    """
)


async def _quoted_records(db: AsyncSession, entity_id: Any, keys: set[str]) -> list[tuple[str, str, list]]:
    rows = (
        await db.execute(_QUOTED_RECORD_SOURCES, {"eid": entity_id, "window": MAX_RECORDS, "keys": sorted(keys)})
    ).mappings().all()
    records: dict[str, tuple[str, list]] = {}
    for r in rows:
        records.setdefault(str(r["event_id"]), (r["event_title"], []))[1].append(r)
    return [(eid, title, rs) for eid, (title, rs) in records.items()]


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
    response: Response,
    limit: int = Query(default=30, ge=1, le=MAX_RECORDS),
    lens: str | None = None,
    db: AsyncSession = Depends(get_db),
) -> EntityPage:
    """One actor and the records it appears in, newest first."""
    # Public and the same for everyone; checking an actor's quotes against
    # their articles is the heaviest read here, so the edge keeps it a while.
    response.headers["Cache-Control"] = ENTITY_CACHE
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

    from api.routes.events import event_claim_verdicts  # events imports indexable_sql from here

    keys = speaker_keys(entity["name"], entity["aliases"])
    # ponytail: verified per request, linear in the quoted records' articles
    # (~110 ms for 60 records x 3 articles locally); the spec's upgrade is a
    # worker-built entity_quotes table. Verdicts are one query per record, and
    # only with PRISM_QUOTE_VERDICTS on: batch them if that flag goes live.
    quoted = await _quoted_records(db, entity["id"], keys) if keys else []
    verdicts = {eid: await event_claim_verdicts(db, eid) for eid, _, _ in quoted}
    quotes, role = entity_quotes(quoted, keys, verdicts)

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
        role=role,
        quote_count=sum(q.speech == "direct" for q in quotes),
        reported_count=sum(q.speech == "reported" for q in quotes),
        quoted_records=len({q.event_id for q in quotes}),
        quotes_window=min(total, MAX_RECORDS),
        quotes=quotes[:MAX_QUOTES],
    )


@router.get("/api/v1/sitemap/entities")
async def sitemap_entities(db: AsyncSession = Depends(get_db)):
    """The actors worth a crawl: slug and last change for every entity in at
    least INDEXABLE_MIN_RECORDS served records. Not a state's own name: that
    address 308s to the state's hub (web/src/app/entity/[slug]), which would
    otherwise compete with it for "<state> news" (audit 02, P1-1)."""
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
                  AND en.slug <> ALL(:state_hubs)
                GROUP BY en.slug
                HAVING count(DISTINCT e.id) >= :floor
                ORDER BY n DESC
                LIMIT 50000
                """
            ),
            {"floor": INDEXABLE_MIN_RECORDS, "state_hubs": sorted(HUB_SLUGS)},
        )
    ).all()
    return {
        "entities": [
            {"slug": r[0], "last_updated_at": r[1].isoformat() if r[1] else None, "record_count": r[2]}
            for r in rows
        ]
    }
