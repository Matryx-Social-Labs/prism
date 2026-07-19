"""Admin routes: static-token guarded operational triggers."""

from fastapi import APIRouter, Header, HTTPException

from common import stream
from common.config import get_settings
from common.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/api/v1/admin/pipeline/run")
async def trigger_pipeline(x_admin_token: str = Header(default="")):
    if x_admin_token != get_settings().prism_admin_token:
        raise HTTPException(status_code=403, detail="invalid admin token")
    # Ingestion runs in the worker; the API only signals it. Running
    # collectors in-process doubled GDELT load and starved API workers.
    await stream.publish(stream.ADMIN_TRIGGERS, {"requested_by": "admin-endpoint"})
    logger.info("admin_trigger_published")
    return {"status": "ingestion trigger queued for worker"}
