"""One scheduled pass: seed the accounts → poll → rematch the hold window → re-check what is shown."""
from common import budget
from common.config import get_settings
from common.logging import get_logger
from xposts.client import XClient
from xposts.compliance import rehydrate
from xposts.match import match_recent
from xposts.poll import poll_all, upsert_accounts

logger = get_logger(__name__)


async def run_xposts() -> dict[str, int]:
    settings = get_settings()
    if not settings.prism_x_enabled:
        logger.info("xposts_disabled", reason="prism_x_enabled=false")
        return {}
    if not settings.x_bearer_token:
        logger.warning("xposts_no_token", reason="X_BEARER_TOKEN empty")
        return {}
    client = XClient(settings.x_bearer_token)
    try:
        await upsert_accounts(client)
        read = await poll_all(client)
        # X reads are prepaid credits, separate from the LLM balance; only the
        # judge spends OpenRouter, so only the match step waits under the floor.
        if budget.below_floor(await budget.current()):
            logger.warning("xposts_budget_floor")
            attached = 0
        else:
            attached = await match_recent()
        deleted = await rehydrate(client)
    finally:
        await client.aclose()
    return {"read": read, "attached": attached, "deleted": deleted}
