"""Pipeline worker: stage consumers + scheduled collectors.

Default (`python -m worker`) runs everything in one process — right for the
prototype and small deployments. For a microservice split, run one stage per
service with `--stages`:

    python -m worker --stages ingestion            # collectors + requeue only
    python -m worker --stages classification
    python -m worker --stages enrichment
    python -m worker --stages correlation
    python -m worker --stages classification,enrichment   # any combination

Each stage is an independent, idempotent consumer group over the Redis
Streams spine, so instances can also be scaled horizontally (Railway
replicas): give each replica a unique PRISM_CONSUMER_NAME.
"""

import argparse
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
CONSUMER_NAME = os.environ.get("PRISM_CONSUMER_NAME", "worker-1")

ALL_STAGES = ["ingestion", "classification", "enrichment", "correlation"]


def parse_stages() -> list[str]:
    parser = argparse.ArgumentParser(prog="python -m worker")
    parser.add_argument(
        "--stages",
        default=os.environ.get("PRISM_STAGES", "all"),
        help="Comma-separated subset of: ingestion,classification,enrichment,correlation (default: all)",
    )
    args = parser.parse_args()
    if args.stages.strip() in ("all", ""):
        return list(ALL_STAGES)
    stages = [s.strip() for s in args.stages.split(",") if s.strip()]
    unknown = set(stages) - set(ALL_STAGES)
    if unknown:
        parser.error(f"unknown stages: {', '.join(sorted(unknown))}")
    return stages


async def _health_server() -> None:
    """Minimal HTTP 200 responder on $PORT.

    Railway applies railway.json's healthcheckPath to every service built
    from it; without this the worker (no HTTP surface) is killed as FAILED
    even while processing fine. Serves any path, so /healthz passes.
    """
    port = int(os.environ.get("PORT", "0"))
    if not port:
        return

    async def handle(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            await reader.read(2048)
            writer.write(b"HTTP/1.1 200 OK\r\nContent-Length: 2\r\nConnection: close\r\n\r\nok")
            await writer.drain()
        finally:
            writer.close()

    server = await asyncio.start_server(handle, "0.0.0.0", port)
    logger.info("worker health endpoint listening on :%d", port)
    async with server:
        await server.serve_forever()


async def main(stages: list[str]) -> None:
    logger.info("prism worker starting (stages: %s, consumer: %s)", ", ".join(stages), CONSUMER_NAME)

    tasks = [asyncio.create_task(_health_server())]

    if "ingestion" in stages:
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
        tasks.append(asyncio.create_task(_initial_ingest()))

    if "classification" in stages:
        tasks.append(
            asyncio.create_task(
                stream.consume(
                    stream.RAW_ITEMS, "classification", handle_raw_item,
                    consumer_name=f"clf-{CONSUMER_NAME}", concurrency=4,
                )
            )
        )
    if "enrichment" in stages:
        tasks.append(
            asyncio.create_task(
                stream.consume(
                    stream.CLASSIFIED_ITEMS, "enrichment", handle_classified_item,
                    consumer_name=f"enr-{CONSUMER_NAME}", concurrency=4,
                )
            )
        )
    if "correlation" in stages:
        # concurrency must stay 1: parallel articles for the same real event
        # would race match-or-create and split the cluster.
        tasks.append(
            asyncio.create_task(
                stream.consume(
                    stream.ENRICHED_ITEMS, "correlation", handle_enriched_item,
                    consumer_name=f"cor-{CONSUMER_NAME}",
                )
            )
        )

    if len(tasks) <= 1:  # only the health server — no stage selected
        raise SystemExit("no stages selected")
    await asyncio.gather(*tasks)


async def _initial_ingest() -> None:
    try:
        await run_all()
    except Exception:
        logger.exception("initial ingestion run failed")


if __name__ == "__main__":
    asyncio.run(main(parse_stages()))
