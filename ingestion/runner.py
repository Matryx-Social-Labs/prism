"""Run all collectors once (called by the worker scheduler and the admin endpoint)."""

from sqlalchemy import select, text

from common import stream
from common.config import get_settings
from common.db import session_scope
from common.logging import get_logger
from common.models import RawItem
from common.schemas import ClassifiedItemMessage, RawItemMessage
from ingestion import cisa_kev, gdelt, nvd, rss
from ingestion.seed import seed_sources

logger = get_logger(__name__)


async def run_all() -> dict[str, int]:
    # Master switch: when disabled, collect nothing and don't requeue stalled
    # items, so no new news enters and the LLM pipeline goes idle (the cost brake).
    if not get_settings().prism_ingestion_enabled:
        logger.info("ingestion_disabled", reason="prism_ingestion_enabled=false")
        return {"disabled": 1}
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
            logger.exception("collector_failed", collector=name)
            results[name] = -1

    results["requeued"] = await requeue_stalled()
    logger.info("ingestion_run_complete", **{f"n_{k}": v for k, v in results.items()})
    return results


async def requeue_stalled(limit: int = 500) -> int:
    """Republish items that stalled mid-pipeline (e.g. LLM outage).

    Safe because every stage handler is idempotent: already-processed items
    are skipped on replay. Covers two gaps: raw items still 'pending' after
    a failed classification, and 'relevant' items that never got an article
    (failed enrichment).
    """
    requeued = 0
    async with session_scope() as session:
        # Only items older than 20 minutes: fresh ones are still in-flight
        # on the stream from their original publish.
        pending = (
            await session.execute(
                select(RawItem.id)
                .where(
                    RawItem.relevance == "pending",
                    RawItem.created_at < text("now() - interval '20 minutes'"),
                )
                .order_by(RawItem.created_at)
                .limit(limit)
            )
        ).scalars().all()

        unenriched = (
            await session.execute(
                text(
                    """
                    SELECT ri.id FROM raw_items ri
                    LEFT JOIN articles a ON a.raw_item_id = ri.id
                    WHERE ri.relevance = 'relevant' AND a.id IS NULL
                      AND ri.updated_at < now() - interval '20 minutes'
                    ORDER BY ri.created_at
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ).scalars().all()

    for raw_id in pending:
        await stream.publish(stream.RAW_ITEMS, RawItemMessage(raw_item_id=str(raw_id)).model_dump())
        requeued += 1
    for raw_id in unenriched:
        await stream.publish(
            stream.CLASSIFIED_ITEMS, ClassifiedItemMessage(raw_item_id=str(raw_id)).model_dump()
        )
        requeued += 1
    return requeued
