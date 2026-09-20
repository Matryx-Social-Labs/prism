"""One scheduled pass: poll → transcribe what is new → rematch the recent window set."""
from common.config import get_settings
from common.logging import get_logger
from podcasts.feeds import poll_all
from podcasts.match import match_recent
from podcasts.transcribe import transcribe_pending

logger = get_logger(__name__)


async def run_podcasts() -> dict[str, int]:
    if not get_settings().prism_podcasts_enabled:
        logger.info("podcasts_disabled", reason="prism_podcasts_enabled=false")
        return {}
    polled = await poll_all()
    windows = await transcribe_pending()
    clips = await match_recent()
    return {"new_episodes": sum(v for v in polled.values() if v > 0), "windows": windows, "clips": clips}
