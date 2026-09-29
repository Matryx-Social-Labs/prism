"""Run all collectors once (called by the worker scheduler and the admin endpoint)."""

from sqlalchemy import select, text

from common import alerts, budget, stream
from common.config import get_settings
from common.db import session_scope
from common.logging import get_logger
from common.models import RawItem
from common.schemas import ClassifiedItemMessage, EnrichedItemMessage, RawItemMessage
from ingestion import rss
from ingestion.seed import seed_sources

logger = get_logger(__name__)

# Dead letters after which requeue_stalled stops re-sending an item: each one
# was a paid attempt that failed permanently (a refusal, an invalid record).
MAX_PERMANENT_FAILURES = 3


async def run_all() -> dict[str, int]:
    # Master switch: when disabled, collect nothing and don't requeue stalled
    # items, so no new news enters and the LLM pipeline goes idle (the cost brake).
    if not get_settings().prism_ingestion_enabled:
        logger.info("ingestion_disabled", reason="prism_ingestion_enabled=false")
        return {"disabled": 1}
    # Stop condition, checked BEFORE any collector runs so hitting the ceiling
    # costs nothing. A cap that is only enforced after collection is a report,
    # not a brake.
    # The balance is a fact the worker recorded; under the floor, collect
    # nothing — the queue must not grow while enrichment cannot follow.
    rec = await budget.current()
    if budget.below_floor(rec):
        logger.warning("ingestion_budget_floor", balance=rec["balance"], floor=get_settings().prism_llm_budget_floor_usd)
        return {"budget_floor": 1}
    cap = get_settings().prism_ingest_max_articles
    if cap:
        async with session_scope() as session:
            held = (
                await session.execute(text("SELECT count(*) FROM articles"))
            ).scalar_one()
        if held >= cap:
            logger.warning("ingestion_cap_reached", articles=held, cap=cap)
            return {"cap_reached": held}

    await seed_sources()
    results: dict[str, int] = {}
    # RSS is the only collector: news, never vulnerability-database records
    # (founder, 2026-09-27 — the NVD and CISA KEV collectors were removed).
    # GDELT is out for now (international + rate-limited) — India-first scope.
    try:
        results["rss"] = await rss.collect()
    except Exception:
        logger.exception("collector_failed", collector="rss")
        results["rss"] = -1

    logger.info("ingestion_run_complete", **{f"n_{k}": v for k, v in results.items()})
    return results


async def requeue_stalled(limit: int = 500) -> int:
    """Republish items that stalled mid-pipeline (e.g. LLM outage).

    Safe because every stage handler is idempotent: already-processed items are
    skipped on replay. Covers the three ways an item can fall out of the
    pipeline without any row saying so: a raw item still 'pending' after a
    failed classification, a 'relevant' item that never got an article (failed
    enrichment), and an enriched article that never reached an event (the
    publish to enriched.items failed, or the message dead-lettered).

    Scheduled on its own, not inside run_all: recovery that only runs while
    ingestion is enabled is off exactly when a cost brake or an outage has
    stopped the pipeline mid-flight (audit H9).
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

        # The third gap (audit H9): the article and its enrichment committed,
        # then the publish to enriched.items failed or the message dead-lettered.
        # Nothing downstream ever sees the article, and no other query notices:
        # to classification it is done, to enrichment it is done, and only the
        # absence of a membership says otherwise.
        uncorrelated = (
            await session.execute(
                text(
                    """
                    SELECT a.raw_item_id, a.id AS article_id, en.id AS enrichment_id
                    FROM articles a
                    JOIN enrichments en ON en.article_id = a.id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    LEFT JOIN event_memberships m ON m.article_id = a.id
                    WHERE m.id IS NULL AND ri.relevance <> 'failed'
                      AND en.created_at < now() - interval '20 minutes'
                    ORDER BY en.created_at
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ).mappings().all()

    spent = await _given_up([*pending, *unenriched, *(row["raw_item_id"] for row in uncorrelated)])
    pending = [i for i in pending if str(i) not in spent]
    unenriched = [i for i in unenriched if str(i) not in spent]
    uncorrelated = [row for row in uncorrelated if str(row["raw_item_id"]) not in spent]

    for raw_id in pending:
        await stream.publish(stream.RAW_ITEMS, RawItemMessage(raw_item_id=str(raw_id)).model_dump())
        requeued += 1
    for raw_id in unenriched:
        await stream.publish(
            stream.CLASSIFIED_ITEMS, ClassifiedItemMessage(raw_item_id=str(raw_id)).model_dump()
        )
        requeued += 1
    for row in uncorrelated:
        await stream.publish(
            stream.ENRICHED_ITEMS,
            EnrichedItemMessage(
                raw_item_id=str(row["raw_item_id"]),
                article_id=str(row["article_id"]),
                enrichment_id=str(row["enrichment_id"]),
            ).model_dump(),
        )
        requeued += 1
    if requeued:
        logger.info(
            "requeued_stalled",
            pending=len(pending),
            unenriched=len(unenriched),
            uncorrelated=len(uncorrelated),
        )
    return requeued


async def _given_up(raw_ids: list) -> set[str]:
    """The items that failed permanently MAX_PERMANENT_FAILURES times: marked
    `failed` so no query picks them up again, and a founder is told. Without the
    counts (Redis away) nothing is given up — that is no evidence of failure."""
    try:
        failures = await stream.permanent_failures([str(i) for i in raw_ids])
    except Exception as exc:  # noqa: BLE001
        logger.warning("failure_counts_unavailable", error=str(exc)[:160])
        return set()
    spent = {i for i, n in failures.items() if n >= MAX_PERMANENT_FAILURES}
    if not spent:
        return spent
    async with session_scope() as session:
        await session.execute(
            text("UPDATE raw_items SET relevance = 'failed', rejection_reason = :why, updated_at = now() "
                 "WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": sorted(spent), "why": f"gave up after {MAX_PERMANENT_FAILURES} permanent failures"},
        )
    logger.warning("requeue_gave_up", count=len(spent), raw_item_ids=sorted(spent)[:20])
    await alerts.notify(
        "requeue-gave-up",
        f"{len(spent)} news items failed for good",
        f"{len(spent)} items failed {MAX_PERMANENT_FAILURES} times without a transient cause (a model refusal or an "
        "invalid record) and will not be retried. They are raw_items with relevance 'failed'; the payloads are in "
        "the dead-letter streams (tools/redrive_dead.py --list).",
    )
    return spent
