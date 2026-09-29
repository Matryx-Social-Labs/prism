"""Meta routes: health, lens registry, taxonomy. No LLM, no heavy queries."""

import json
import time

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    FeedOut,
    LensesResponse,
    LensOut,
    SectorOut,
    SourcesResponse,
    SubsectorOut,
    TaxonomyResponse,
)
from common import outlets
from common.db import get_db
from common.embeddings import check_corpus_model
from common.freshness import MAX_WINDOW_HOURS, MIN_WINDOW_HOURS, WINDOW_HOURS, pipeline_freshness
from common.lenses import DEFAULT_LENS, active_lenses
from common.logging import get_logger
from common.outlets import monitored, record_indexable
from common.stream import backlog
from common.taxonomy import TAXONOMY, display_name

router = APIRouter()
logger = get_logger(__name__)


@router.get("/healthz")
async def healthz(
    db: AsyncSession = Depends(get_db),
    freshness_window_hours: int = Query(
        default=WINDOW_HOURS,
        ge=MIN_WINDOW_HOURS,
        le=MAX_WINDOW_HOURS,
        description="Recent observation window used for stage-latency telemetry.",
    ),
):
    """Liveness, plus the queue depth behind each stage.

    `SELECT 1` alone was the whole check, and it is exactly the wrong thing to
    measure: the pipeline's characteristic failure is not a database that stopped
    answering, it is a stage that keeps answering while its backlog grows. On
    2026-09-03 the gate approved items ~35x faster than enrichment consumed them,
    1,023 relevant articles were collected and never enriched, and nothing
    anywhere reported it. The only stream-size code in the repo was STREAM_MAXLEN,
    which silently DISCARDS old entries at 100k.

    Never fails the check on a backlog. A deep queue is a capacity problem, not a
    liveness problem, and a health endpoint that goes red on one would take the
    API out of rotation for a condition the API cannot cause or fix.
    """
    await db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "streams": await backlog(),
        "freshness": await pipeline_freshness(db, window_hours=freshness_window_hours),
        "embeddings": await check_corpus_model(db),
    }


@router.get("/api/v1/lenses", response_model=LensesResponse)
async def get_lenses():
    return LensesResponse(
        lenses=[
            LensOut(slug=lens.slug, name=lens.name, tagline=lens.tagline)
            for lens in active_lenses()  # shipped lenses only; upcoming drafts excluded
        ],
        default=DEFAULT_LENS,
    )


@router.get("/api/v1/sources", response_model=SourcesResponse)
async def get_sources(db: AsyncSession = Depends(get_db)):
    """The outlets Prism monitors, each with its last poll: the public source
    list, and the denominator every story's outlet count is out of. No feed URL,
    no error text: what is read and whether it answered, nothing operational."""
    m = await monitored(db)
    return SourcesResponse(
        outlets=m.outlets,
        checked_at=m.checked_at,
        feeds=[FeedOut(**{k: getattr(f, k) for k in FeedOut.model_fields}) for f in m.feeds],
    )


# A browser posts a CSP violation here while the policy is report-only
# (web/next.config.ts). Logged in one compact line so a wrong allowance shows up
# in the API logs before anything is enforced. Public and unauthenticated by
# nature, so the body is capped and at most CSP_LOGS_PER_MINUTE are logged.
# ponytail: a per-process minute window; a shared counter if it ever matters.
CSP_LOGS_PER_MINUTE = 60
_csp_window: list[float] = [0.0, 0]


@router.post("/api/v1/csp-report", status_code=204)
async def csp_report(request: Request):
    body = (await request.body())[:8192]
    now = time.monotonic()
    if now - _csp_window[0] >= 60:
        _csp_window[0], _csp_window[1] = now, 0
    if _csp_window[1] >= CSP_LOGS_PER_MINUTE:
        return Response(status_code=204)
    _csp_window[1] += 1
    try:
        data = json.loads(body or b"{}")
    except ValueError:
        return Response(status_code=204)
    # application/csp-report wraps it in "csp-report"; Reporting API sends a list.
    report = data.get("csp-report", data) if isinstance(data, dict) else (data[0].get("body", {}) if data else {})
    if isinstance(report, dict):
        logger.warning(
            "csp_violation",
            directive=str(report.get("effective-directive") or report.get("violated-directive") or report.get("effectiveDirective"))[:80],
            blocked=str(report.get("blocked-uri") or report.get("blockedURL") or "")[:200],
            page=str(report.get("document-uri") or report.get("documentURL") or "")[:200],
        )
    return Response(status_code=204)


@router.get("/api/v1/regions")
async def get_regions():
    """Indian states/UTs for onboarding (with a `covered` flag per state)."""
    from common.regions import states_payload

    return {"country": "IN", "states": states_payload()}


@router.get("/api/v1/sitemap/records")
async def sitemap_records(db: AsyncSession = Depends(get_db)):
    """Every served record's id and last change, newest first, for the records
    sitemap — the feed pages at 100 and the archive was invisible to crawlers
    past the freshest hundred (audit H30). Capped at the sitemap protocol's
    50,000 URLs per file; page this endpoint when the corpus passes it.

    Only records that ask to be indexed (common/outlets.record_indexable: two
    outlets or more), so the sitemap never offers a page whose robots say no.
    Two sources is the SQL's cut; two publishers is the rule's.

    `lastmod` is the newest report's publication (the projection's
    `latest_published_at`), never after the record was last rebuilt with it:
    `last_updated_at` alone is the rebuild clock, and hundreds of URLs sharing
    one rebuild hour is what makes Google stop trusting lastmod (audit 01
    P2-11). A record without a dated report falls back to the rebuild clock."""
    rows = (
        await db.execute(
            text(
                """
                SELECT id,
                       LEAST(COALESCE((projection->>'latest_published_at')::timestamptz, last_updated_at),
                             last_updated_at),
                       projection->'source_slugs'
                FROM events
                WHERE COALESCE(jsonb_array_length(projection->'source_slugs'), 0) >= 2
                  AND merged_into IS NULL
                ORDER BY last_updated_at DESC LIMIT 50000
                """
            )
        )
    ).all()
    reg = await outlets.registry(db)
    return {"records": [
        {"id": str(r[0]), "lastmod": r[1].isoformat() if r[1] else None}
        for r in rows if record_indexable(r[2] or [], reg)
    ]}


NEWS_SITEMAP_CAP = 1000  # Google News reads at most 1,000 URLs per sitemap


@router.get("/api/v1/sitemap/news")
async def sitemap_news(db: AsyncSession = Depends(get_db)):
    """The news sitemap's records: every served record that asks to be indexed
    (the records sitemap's rule) and was FIRST reported in the last 48 hours,
    which is all Google News reads. Its own query: the web used to filter the
    feed's newest hundred and listed about 10 of the hundreds eligible (audit
    A4). The date is the first report's publication, never when we last
    touched the record, and a record whose reports carry no date is not listed.

    `last_updated_at` bounds the scan first (its index): a record first
    reported in the window was necessarily rebuilt inside it."""
    rows = (
        await db.execute(
            text(
                """
                SELECT e.id, e.title, f.published_at, e.projection->'source_slugs' FROM events e
                CROSS JOIN LATERAL (
                    SELECT min(ri.published_at) AS published_at
                    FROM event_memberships em
                    JOIN articles a ON a.id = em.article_id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    WHERE em.event_id = e.id
                ) f
                WHERE COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) >= 2
                  AND e.merged_into IS NULL
                  AND e.last_updated_at >= now() - interval '48 hours'
                  AND f.published_at >= now() - interval '48 hours'
                ORDER BY f.published_at DESC
                """
            )
        )
    ).all()
    reg = await outlets.registry(db)
    listed = [r for r in rows if record_indexable(r[3] or [], reg)][:NEWS_SITEMAP_CAP]
    return {"records": [{"id": str(r[0]), "title": r[1], "published_at": r[2].isoformat()} for r in listed]}


ATOM_ENTRIES = 50
_ATOM_SCAN = 200  # two sources in SQL can be one publisher (two feeds of one masthead)


@router.get("/api/v1/sitemap/atom")
async def sitemap_atom(db: AsyncSession = Depends(get_db)):
    """The Atom feed's records (web /feed.xml): the newest records that ask to
    be indexed (the records sitemap's rule), newest report first. `updated` is
    the newest report's publication, never when Prism last rebuilt the record,
    and never later than that rebuild: a feed that stamps its report in the
    future cannot pin a record to the top. A record whose reports carry no
    date is not listed. `summary` is the record's own, never article text."""
    rows = (
        await db.execute(
            text(
                """
                SELECT id, title, summary, projection->'source_slugs' AS slugs,
                       LEAST((projection->>'latest_published_at')::timestamptz, last_updated_at) AS updated
                FROM events
                WHERE COALESCE(jsonb_array_length(projection->'source_slugs'), 0) >= 2
                  AND merged_into IS NULL
                  AND projection->>'latest_published_at' IS NOT NULL
                ORDER BY updated DESC LIMIT :scan
                """
            ),
            {"scan": _ATOM_SCAN},
        )
    ).mappings().all()
    reg = await outlets.registry(db)
    listed = [r for r in rows if record_indexable(r["slugs"] or [], reg)][:ATOM_ENTRIES]
    return {"records": [
        {"id": str(r["id"]), "title": r["title"], "summary": r["summary"] or None, "updated": r["updated"].isoformat()}
        for r in listed
    ]}


@router.get("/api/v1/taxonomy", response_model=TaxonomyResponse)
async def get_taxonomy():
    return TaxonomyResponse(
        sectors=[
            SectorOut(
                slug=sector,
                name=display_name(sector),
                subsectors=[SubsectorOut(slug=sub, name=display_name(sub)) for sub in subs],
            )
            for sector, subs in TAXONOMY.items()
        ]
    )
