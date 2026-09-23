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
import os
from datetime import UTC, datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from classification.consumer import handle_raw_item
from common import stream
from common.logging import get_logger, setup_logging
from correlation.consumer import handle_enriched_item, run_due_analyses
from enrichment.consumer import handle_classified_item
from ingestion.runner import requeue_stalled, run_all

setup_logging()
logger = get_logger("worker")

INGEST_INTERVAL_MINUTES = int(os.environ.get("PRISM_INGEST_INTERVAL_MINUTES", "5"))
REQUEUE_INTERVAL_MINUTES = int(os.environ.get("PRISM_REQUEUE_INTERVAL_MINUTES", "10"))
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


SWEEP_INTERVAL_S = 5


BUDGET_INTERVAL_S = int(os.environ.get("PRISM_BUDGET_INTERVAL_S", "900"))
# LLM calls in flight for enrichment. OpenRouter reserves each call's ceiling
# against the balance, so this is also how hard the pipeline leans on it;
# lower it (a redeploy) when the balance is thin.
ENRICH_CONCURRENCY = int(os.environ.get("PRISM_ENRICH_CONCURRENCY", "12"))


async def _budget_watch() -> None:
    """Record the LLM balance every fifteen minutes (common/budget.py)."""
    from common import budget

    while True:
        try:
            await budget.refresh()
        except Exception:
            logger.exception("budget_watch_error")
        await asyncio.sleep(BUDGET_INTERVAL_S)


async def _analysis_sweeper() -> None:
    """Poll for due (debounced) story analyses and run them off the ingest path."""
    while True:
        try:
            await run_due_analyses()
        except Exception:
            logger.exception("analysis_sweeper_error")
        await asyncio.sleep(SWEEP_INTERVAL_S)


TRENDING_INTERVAL_S = int(os.environ.get("PRISM_TRENDING_INTERVAL_S", "600"))


async def _trending_reconciler() -> None:
    """Reconcile trending stories on an interval, off the ingest path. Keeps the
    /trending slugs stable (see correlation/trending.py)."""
    from common.db import session_scope
    from correlation.trending import reconcile_stories

    while True:
        await asyncio.sleep(TRENDING_INTERVAL_S)
        try:
            async with session_scope() as session:
                await reconcile_stories(session)
        except Exception:
            logger.exception("trending_reconciler_error")


PARTITION_INTERVAL_S = int(os.environ.get("PRISM_PARTITION_INTERVAL_S", "900"))  # base L2 pass (cheap)
VETO_INTERVAL_S = int(os.environ.get("PRISM_VETO_INTERVAL_S", "3600"))  # overlay veto pass (LLM)


async def _partition_reconciler() -> None:
    """Republish the global storyline partition (base L2) on an interval — the
    consistent boundary every story_timeline reads (correlation/partition.py). Cheap,
    no LLM; the veto refines it separately below."""
    from correlation.partition import persist_base_run

    while True:
        await asyncio.sleep(PARTITION_INTERVAL_S)
        try:
            await persist_base_run()
        except Exception:
            logger.exception("partition_reconciler_error")


async def _veto_reconciler() -> None:
    """Refine the current base run with the grounded LLM veto on a slower cadence,
    publishing an overlay run only if its base is still current (correlation/
    partition.py::persist_veto_overlay)."""
    from correlation.partition import persist_veto_overlay

    while True:
        await asyncio.sleep(VETO_INTERVAL_S)
        try:
            await persist_veto_overlay()
        except Exception:
            logger.exception("veto_reconciler_error")


QUOTES_INTERVAL_S = int(os.environ.get("PRISM_QUOTES_INTERVAL_S", "900"))


async def _quote_reconciler() -> None:
    """Judge the speaker cards a new report changed: which quotes are one
    statement printed in two languages, which an outlet's translation
    (enrichment/renderings.py). Off the ingest path, and only when
    PRISM_QUOTE_VERDICTS is on for this service — on the worker alone it is a
    shadow run that writes claim_verdicts and serves nothing."""
    from common.config import get_settings
    from enrichment.renderings import sweep

    while True:
        await asyncio.sleep(QUOTES_INTERVAL_S)
        if not get_settings().prism_quote_verdicts:
            continue
        try:
            await sweep()  # commits per event; see its docstring
        except Exception:
            logger.exception("quote_reconciler_error")


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
    logger.info("health_endpoint_listening", port=port)
    async with server:
        await server.serve_forever()


async def main(stages: list[str]) -> None:
    logger.info("worker_starting", stages=stages, consumer=CONSUMER_NAME)

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
        # Recovery is its own job, NOT part of run_all: it used to ride inside
        # the collector pass, so turning ingestion off (the cost brake, or a
        # budget floor) also turned off the only thing that re-drives items
        # stranded mid-pipeline — exactly when there are most of them (audit H9).
        scheduler.add_job(
            requeue_stalled,
            IntervalTrigger(minutes=REQUEUE_INTERVAL_MINUTES),
            id="requeue",
            max_instances=1,
            coalesce=True,
        )
        # Podcast clips ride the same scheduler, hourly: poll five feeds,
        # transcribe what is new, rematch. A no-op unless PRISM_PODCASTS_ENABLED.
        from podcasts.runner import run_podcasts

        # First run at startup: a deploy restarts the worker and the interval
        # with it, and on a day of hourly promotes an hour-from-now job never
        # arrives (2026-09-20: flag on for three hours, zero runs).
        scheduler.add_job(
            run_podcasts, IntervalTrigger(minutes=60), id="podcasts", max_instances=1, coalesce=True,
            next_run_time=datetime.now(UTC) + timedelta(seconds=90),
        )
        # X posts from the official accounts, every PRISM_X_POLL_MINUTES: poll
        # by since_id, rematch the 72 h hold, re-check what is shown. A no-op
        # unless PRISM_X_ENABLED and X_BEARER_TOKEN.
        from xposts.runner import run_xposts

        scheduler.add_job(
            run_xposts, IntervalTrigger(minutes=int(os.environ.get("PRISM_X_POLL_MINUTES", "10"))),
            id="xposts", max_instances=1, coalesce=True,
            next_run_time=datetime.now(UTC) + timedelta(seconds=120),
        )
        # Subscriptions: ask Razorpay about rows the webhook may have missed
        # (checkouts still 'created', entitled rows untouched for a day). A
        # missed webhook must never leave a paying reader on the free plan.
        from common.db import session_scope as _scope
        from common.razorpay import reconcile_pending, resume_due

        async def _reconcile_billing() -> None:
            async with _scope() as s:
                n = await reconcile_pending(s)
                resumed = await resume_due(s)
            if n or resumed:
                logger.info("billing_reconciled", changed=n, resumed=resumed)

        # IndexNow: the records and stories that moved in the last hour go to
        # Bing/Yandex/Naver at once (common/indexnow); Google reads the sitemaps.
        async def _indexnow() -> None:
            from common.indexnow import ping_changed

            async with _scope() as s:
                await ping_changed(s)

        scheduler.add_job(
            _reconcile_billing, IntervalTrigger(minutes=60), id="billing_reconcile", max_instances=1, coalesce=True,
            next_run_time=datetime.now(UTC) + timedelta(seconds=120),
        )
        scheduler.add_job(
            _indexnow, IntervalTrigger(minutes=60), id="indexnow", max_instances=1, coalesce=True,
            next_run_time=datetime.now(UTC) + timedelta(seconds=300),
        )
        scheduler.start()
        # Kick off one ingestion run at startup so a fresh deploy has data.
        tasks.append(asyncio.create_task(_initial_ingest()))
        # Admin-triggered runs arrive over the stream (the API never ingests
        # in-process); overlapping triggers coalesce behind one lock.
        tasks.append(
            asyncio.create_task(
                stream.consume(
                    stream.ADMIN_TRIGGERS, "ingestion", _handle_admin_trigger,
                    consumer_name=f"ing-{CONSUMER_NAME}",
                )
            )
        )

    # Before any stage that WRITES vectors. Enrichment embeds every article, so
    # starting it against a corpus embedded by another model silently mixes two
    # incomparable distance scales — measured at 25x the false merges, with
    # nothing logged. A refusal is visible; a corrupted feed is not.
    if {"enrichment", "correlation"} & set(stages):
        from common.db import session_scope
        from common.embeddings import assert_corpus_model

        async with session_scope() as _s:
            await assert_corpus_model(_s)

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
                    # Enrichment's cost is the LLM extract (I/O-bound) — parallelize
                    # it so a slow-but-reliable model keeps up with ingest.
                    #
                    # IT DOES NOT KEEP UP, measured 2026-09-03 on a cold start after
                    # a month with ingestion off. Over six minutes: 5,690 raw items
                    # collected, 637 passed the relevance gate, and 19 became
                    # articles. The gate approves ~6,000/hour; enrichment consumes
                    # ~180/hour. A 33x mismatch, so the queue grows ~5,800/hour and
                    # most of the spend buys triage for work that will never happen
                    # — $0.40 for 19 usable articles, against a recorded steady-state
                    # cost of $1.55 per 1,000.
                    #
                    # THAT DIAGNOSIS WAS WRONG, and the correction is worth keeping.
                    # "The ceiling is per-article latency, not slot count" does not
                    # survive arithmetic: components measured 2026-09-04 are fulltext
                    # 0.42s median, embed 0.107s, extract 2.61s — ~3.14s, which across
                    # 12 slots is ~13,700 articles/hour, not 180.
                    #
                    # The ceiling was the BATCH BARRIER in common/stream.consume: it
                    # read a batch, gather()ed all of it, and only read the next batch
                    # once every message finished. With batch_size == concurrency == 12
                    # the semaphore bounded nothing and throughput was
                    # batch_size / slowest-of-the-batch. One slow article idled eleven
                    # workers. Fixed by a pool of persistent workers; see the comment
                    # there and tests/test_stream_pool.py.
                    #
                    # Two contributing faults are also gone: the LLM client had no
                    # timeout (600s default, so a hung call held a slot for ten
                    # minutes), and the extract model was returning a bare number for
                    # every call, so roughly half of each attempt was paid for and
                    # discarded. Re-measure before tuning this number again.
                    consumer_name=f"enr-{CONSUMER_NAME}", concurrency=ENRICH_CONCURRENCY, batch_size=ENRICH_CONCURRENCY,
                )
            )
        )
    if "correlation" in stages:
        # Kept at 1 for throughput reasons only: match-or-create now takes an
        # advisory lock on the database (correlation/consumer._attach) and an
        # article can belong to one event by constraint, so a second replica or
        # a higher concurrency is safe, just serialised at the lock.
        tasks.append(
            asyncio.create_task(
                stream.consume(
                    stream.ENRICHED_ITEMS, "correlation", handle_enriched_item,
                    consumer_name=f"cor-{CONSUMER_NAME}",
                )
            )
        )
        # Debounced analysis sweeper: attach is real-time (above); the expensive
        # per-story LLM analysis runs here, coalesced, off the ingest hot path.
        tasks.append(asyncio.create_task(_analysis_sweeper()))
        tasks.append(asyncio.create_task(_budget_watch()))
        tasks.append(asyncio.create_task(_trending_reconciler()))
        tasks.append(asyncio.create_task(_partition_reconciler()))
        tasks.append(asyncio.create_task(_veto_reconciler()))
        tasks.append(asyncio.create_task(_quote_reconciler()))

    if len(tasks) <= 1:  # only the health server — no stage selected
        raise SystemExit("no stages selected")
    await asyncio.gather(*tasks)


_ingest_lock = asyncio.Lock()


async def _handle_admin_trigger(payload: dict) -> None:
    if _ingest_lock.locked():
        logger.info("admin_trigger_coalesced", reason="ingestion already running")
        return
    async with _ingest_lock:
        logger.info("admin_trigger_received", requested_by=payload.get("requested_by", "api"))
        await run_all()


async def _initial_ingest() -> None:
    try:
        async with _ingest_lock:
            await run_all()
    except Exception:
        logger.exception("initial_ingest_failed")


if __name__ == "__main__":
    asyncio.run(main(parse_stages()))
