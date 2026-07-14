"""Run all collectors once (called by the worker scheduler and the admin endpoint)."""

import logging

from ingestion import cisa_kev, gdelt, nvd, rss
from ingestion.seed import seed_sources

logger = logging.getLogger(__name__)


async def run_all() -> dict[str, int]:
    await seed_sources()
    results: dict[str, int] = {}
    for name, collector in (
        ("cisa_kev", cisa_kev.collect),
        ("nvd", nvd.collect),
        ("gdelt", gdelt.collect),
        ("rss", rss.collect),
    ):
        try:
            results[name] = await collector()
        except Exception:
            logger.exception("collector %s failed", name)
            results[name] = -1
    logger.info("ingestion run complete: %s", results)
    return results
