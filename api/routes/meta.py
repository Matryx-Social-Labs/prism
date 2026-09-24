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
from common.db import get_db
from common.embeddings import check_corpus_model
from common.freshness import MAX_WINDOW_HOURS, MIN_WINDOW_HOURS, WINDOW_HOURS, pipeline_freshness
from common.lenses import DEFAULT_LENS, active_lenses
from common.logging import get_logger
from common.outlets import monitored
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
    50,000 URLs per file; page this endpoint when the corpus passes it."""
    rows = (
        await db.execute(
            text(
                """
                SELECT id, last_updated_at FROM events
                WHERE COALESCE(jsonb_array_length(projection->'source_slugs'), 0) > 0
                ORDER BY last_updated_at DESC LIMIT 50000
                """
            )
        )
    ).all()
    return {"records": [{"id": str(r[0]), "last_updated_at": r[1].isoformat() if r[1] else None} for r in rows]}


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
