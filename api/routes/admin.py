"""Admin routes: static-token guarded operational triggers, and the /admin
dashboard's own account-guarded routes (founder decision D1, 2026-09-23)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import require_admin, require_admin_user
from common import admin_audit, budget, stream
from common.config import get_settings
from common.db import get_db
from common.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("/api/v1/admin/status", dependencies=[Depends(require_admin)])
async def pipeline_status():
    """What the pipeline knows about itself: the LLM balance the worker last
    recorded and the floor it stops collecting under. Absent until the worker
    has asked OpenRouter once."""
    rec = await budget.current()
    return {
        "llm_balance_usd": rec["balance"] if rec else None,
        "llm_balance_at": rec["at"] if rec else None,
        "llm_budget_floor_usd": get_settings().prism_llm_budget_floor_usd,
        "collecting": not budget.below_floor(rec),
    }


@router.post("/api/v1/admin/pipeline/run", dependencies=[Depends(require_admin)])
async def trigger_pipeline():
    # Ingestion runs in the worker; the API only signals it. Running
    # collectors in-process doubled GDELT load and starved API workers.
    await stream.publish(stream.ADMIN_TRIGGERS, {"requested_by": "admin-endpoint"})
    logger.info("admin_trigger_published")
    return {"status": "ingestion trigger queued for worker"}


@router.get("/api/v1/admin/me")
async def admin_me(email: str = Depends(require_admin_user)):
    """Whether this account may open /admin. The page asks before it shows
    anything; the routes behind it check again on every call."""
    return {"email": email}


@router.get("/api/v1/admin/audit")
async def admin_audit_log(
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    _: str = Depends(require_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return {"entries": await admin_audit.recent(db, limit)}
