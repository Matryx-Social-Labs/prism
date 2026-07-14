"""Pipeline worker: all stage consumers + scheduled collectors in one process.

Run with `python -m worker`. On Railway this is the `worker` service; the
stages can be split into separate services later without code changes
(each consumer is independent and idempotent).
"""

import asyncio
import logging
import os

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from classification.consumer import handle_raw_item
from common import stream
from correlation.consumer import handle_enriched_item
from enrichment.consumer import handle_classified_item
from ingestion.runner import run_all

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("worker")

INGEST_INTERVAL_MINUTES = int(os.environ.get("PRISM_INGEST_INTERVAL_MINUTES", "30"))


async def main() -> None:
    logger.info("prism worker starting")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_all,
        IntervalTrigger(minutes=INGEST_INTERVAL_MINUTES),
        id="ingestion",
        max_instances=1,
        coalesce=True,
    )
    scheduler.start()

    # Kick off one ingestion run at startup so a fresh deploy has data.
    asyncio.create_task(_initial_ingest())

    consumers = [
        stream.consume(stream.RAW_ITEMS, "classification", handle_raw_item, consumer_name="clf-1"),
        stream.consume(stream.CLASSIFIED_ITEMS, "enrichment", handle_classified_item, consumer_name="enr-1"),
        stream.consume(stream.ENRICHED_ITEMS, "correlation", handle_enriched_item, consumer_name="cor-1"),
    ]
    await asyncio.gather(*consumers)


async def _initial_ingest() -> None:
    try:
        await run_all()
    except Exception:
        logger.exception("initial ingestion run failed")


if __name__ == "__main__":
    asyncio.run(main())
