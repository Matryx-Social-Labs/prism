"""Meta routes: health, lens registry, taxonomy. No LLM, no heavy queries."""

from fastapi import APIRouter, Depends
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
from common.lenses import LENSES
from common.taxonomy import TAXONOMY, display_name

router = APIRouter()


@router.get("/healthz")
async def healthz(db: AsyncSession = Depends(get_db)):
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}


@router.get("/api/v1/lenses", response_model=LensesResponse)
async def get_lenses():
    return LensesResponse(
        lenses=[
            LensOut(slug=lens.slug, name=lens.name, tagline=lens.tagline)
            for lens in LENSES.values()
        ],
        default="cyber_grc",
    )


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
