"""Meta routes: health, lens registry, taxonomy. No LLM, no heavy queries."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas import (
    LensesResponse,
    LensOut,
    SectorOut,
    SubsectorOut,
    TaxonomyResponse,
)
from common.db import get_db
from common.embeddings import check_corpus_model
from common.freshness import MAX_WINDOW_HOURS, MIN_WINDOW_HOURS, WINDOW_HOURS, pipeline_freshness
from common.lenses import DEFAULT_LENS, active_lenses
from common.stream import backlog
from common.taxonomy import TAXONOMY, display_name

router = APIRouter()


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


@router.get("/api/v1/regions")
async def get_regions():
    """Indian states/UTs for onboarding (with a `covered` flag per state)."""
    from common.regions import states_payload

    return {"country": "IN", "states": states_payload()}


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
