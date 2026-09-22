"""Admin routes: static-token guarded operational triggers."""

from fastapi import APIRouter, Depends

from api.deps import require_admin
from common import budget, stream
from common.config import get_settings
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
