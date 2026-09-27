"""/admin: the product's numbers (admin dashboard, phase C).

GET /api/v1/admin/metrics?days=28        — visits, sign-ups, engagement, money, demand, supply
GET /api/v1/admin/metrics/weekly.csv     — one row per IST week, counts only, for investors
GET /api/v1/admin/coverage?days=28       — outlets linked by the stories they share (common/coverage)
GET /api/v1/admin/spend?days=14          — model spend per stage per day (common/spend) + the balance

Founder-only (api/deps.require_admin_user). common/metrics says what every
number is, where it is counted, and what is deliberately not computed.
"""

from __future__ import annotations

import csv
import io
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin_user
from common import budget, coverage, metrics, spend
from common.config import get_settings
from common.db import get_db

router = APIRouter()
PRIVATE = {"Cache-Control": "no-store"}


@router.get("/api/v1/admin/metrics")
async def dashboard(
    response: Response,
    # Bounded: every section scans its window twice (this period and the last).
    days: Annotated[int, Query(ge=1, le=366)] = 28,
    _: str = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers.update(PRIVATE)
    return await metrics.dashboard(db, days)


@router.get("/api/v1/admin/metrics/weekly.csv")
async def weekly_csv(
    weeks: Annotated[int, Query(ge=1, le=104)] = 12,
    _: str = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
) -> Response:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=metrics.WEEKLY_COLUMNS)
    writer.writeheader()
    writer.writerows(await metrics.weekly(db, weeks))
    return Response(buf.getvalue(), media_type="text/csv",
                    headers={**PRIVATE, "Content-Disposition": 'attachment; filename="prism-weekly.csv"'})


@router.get("/api/v1/admin/coverage")
async def coverage_network(
    response: Response,
    days: Annotated[int, Query(ge=1, le=366)] = 28,
    _: str = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers.update(PRIVATE)
    return await coverage.network(db, metrics.window(days))


@router.get("/api/v1/admin/spend")
async def model_spend(
    response: Response,
    days: Annotated[int, Query(ge=1, le=spend.KEEP_DAYS)] = 14,
    _: str = Depends(require_admin_user),
):
    """What the models cost, per stage per day, from the ledger every model call
    writes (common/spend). Days before the ledger existed come back
    `recorded: false` — absent, not zero."""
    response.headers.update(PRIVATE)
    return {"days": await spend.days(days), "balance": await budget.current(),
            "floor": get_settings().prism_llm_budget_floor_usd}
