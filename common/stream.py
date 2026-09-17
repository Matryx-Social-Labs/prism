"""Streaming spine — Redis Streams for the prototype.

Every stage is a consumer of one topic and a producer to the next
(ARCHITECTURE.md "stream, not batch"). This module is the only place that
talks to the broker, so swapping Redis Streams for Kafka/Redpanda/NATS
later means reimplementing publish/consume, not touching stage logic.
"""

import asyncio
import json
import os
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis

from common.config import get_settings
from common.logging import get_logger

logger = get_logger(__name__)

# Topics per docs/DB-SCHEMA.md (feed.updates deferred with real personalization)
RAW_ITEMS = "raw.items"
CLASSIFIED_ITEMS = "classified.items"
ENRICHED_ITEMS = "enriched.items"
ADMIN_TRIGGERS = "admin.triggers"  # api -> worker: run ingestion now

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        # No health_check_interval: its PING desyncs blocking XREADGROUP
        # reads (every read then times out). Keepalive + connect timeout only.
        _redis = aioredis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_keepalive=True,
        )
    return _redis


# Redis streams do NOT drop entries on XACK — an acknowledged message stays in
# the stream forever unless something trims it. Nothing did, so every topic grew
# without bound: measured in production at 306,509 entries across five streams
# (raw.items alone at 141,185). That ends with Redis hitting its memory limit and
# the pipeline stopping, with no prior symptom.
#
# `approximate=True` lets Redis trim on radix-node boundaries, which is far
# cheaper than exact trimming and overshoots by at most a node. The cap is huge
# relative to throughput (~1k items per 30-minute ingest run), so a consumer that
# is behind — or reclaiming after a crash, which XAUTOCLAIM allows up to 5 min —
# has orders of magnitude of headroom before anything it still needs is trimmed.
STREAM_MAXLEN = int(os.environ.get("PRISM_STREAM_MAXLEN", "100000"))


async def backlog() -> dict[str, dict[str, int]]:
    """Undelivered, in-flight, stalled, and dead-letter counts per topic.

    `pending` is the consumer group's PEL — messages handed out and not yet
    acked. `waiting` is what has not been handed out at all: the number that
    grows without limit when a stage cannot keep up, and the one nobody could
    see while 1,023 articles were dropped.

    Best-effort by construction. This is called from /healthz, so a Redis hiccup
    must degrade the report, never fail the health check.
    """
    r = get_redis()
    out: dict[str, dict[str, int]] = {}
    for topic, group in (
        (RAW_ITEMS, "classification"),
        (CLASSIFIED_ITEMS, "enrichment"),
        (ENRICHED_ITEMS, "correlation"),
    ):
        report = {
            "waiting": -1,
            "pending": -1,
            "oldest_pending_ms": -1,
            "dead_lettered": -1,
        }
        try:
            groups = await r.xinfo_groups(topic)
            info = next((g for g in groups if str(g.get("name")) == group), {})
            report["waiting"] = int(info.get("lag") or 0)
            report["pending"] = int(info.get("pending") or 0)
            if report["pending"] == 0:
                report["oldest_pending_ms"] = 0
            else:
                try:
                    rows = await r.xpending_range(topic, group, min="-", max="+", count=1)
                    row = rows[0] if rows else {}
                    report["oldest_pending_ms"] = int(
                        row.get("time_since_delivered", row.get("idle", -1))
                    )
                except Exception:
                    # Queue depth is still useful if only XPENDING detail fails.
                    pass
        except Exception:
            pass  # -1 means unknown, not zero
        try:
            report["dead_lettered"] = int(await r.xlen(f"{topic}.dead"))
        except Exception:
            pass
        out[topic] = report
    return out


async def publish(topic: str, message: dict) -> str:
    """Publish a JSON message to a topic. Returns the stream entry id."""
    r = get_redis()
    entry_id = await r.xadd(
        topic, {"data": json.dumps(message, default=str)},
        maxlen=STREAM_MAXLEN, approximate=True,
    )
    return entry_id


STALE_CLAIM_IDLE_MS = 300_000  # reclaim messages a dead consumer held > 5 min
# A live handler renews its claim this often, so a message being processed for
# longer than the idle threshold (an LLM cooldown of 120s, retries, a slow
# model) is never mistaken for a dead consumer's and worked twice. Measured
# 2026-09-17: six raw items got two articles each this way under the 402s.
HEARTBEAT_S = 60
async def consume(
    topic: str,
    group: str,
    handler: Callable[[dict], Awaitable[None]],
    consumer_name: str = "worker-1",
    block_ms: int = 5000,
    batch_size: int = 10,
    concurrency: int = 1,
) -> None:
    """Consume a topic forever with a consumer group.

    Permanent failures are logged, copied to ``<topic>.dead``, and acked — the
    DB keeps the authoritative state, so a stage can be re-driven from persisted
    rows; poison messages must not wedge the stream. Transient infrastructure
    failures remain pending regardless of delivery count and recover through
    XAUTOCLAIM. Messages
    stranded in a dead consumer's pending list (e.g. after a restart under
    a different consumer name) are reclaimed via XAUTOCLAIM.

    `concurrency` is the number of PERSISTENT workers, safe above 1 only for
    handlers whose items are independent (classification, enrichment);
    correlation must stay at 1 or concurrent articles for the same real event
    would race the match-or-create and split the cluster.
    """
    r = get_redis()
    try:
        await r.xgroup_create(topic, group, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    logger.info("consumer_started", topic=topic, group=group, consumer=consumer_name)

    # A POOL OF PERSISTENT WORKERS, not a batch drained under gather().
    #
    # The previous shape read a batch, gather()ed all of it, and only read the
    # next batch once EVERY message had finished. With batch_size == concurrency
    # == 12 for enrichment the semaphore bounded nothing, and throughput was
    # batch_size / slowest-of-the-batch rather than concurrency / mean: one slow
    # article idled eleven workers until it returned.
    #
    # That is the ceiling nobody could find, and it is why the note in
    # worker/__main__.py concluding "the ceiling is per-article latency, not slot
    # count" was wrong. Components measured 2026-09-04 — fulltext 0.42s median,
    # embed 0.107s, extract 2.61s — total ~3.14s, which across 12 slots is
    # ~13,700 articles/hour. The best hour ever observed was ~546 and the
    # 2026-09-03 run managed ~172 against a gate approving ~6,000. 1,023 relevant
    # articles were collected, paid for, and never enriched.
    #
    # Here a slow message occupies ONE worker and the reader keeps feeding the
    # rest. At concurrency=1 this is exactly the old sequential behaviour.
    queue: asyncio.Queue = asyncio.Queue(maxsize=max(concurrency, 1))

    async def _worker() -> None:
        while True:
            message = await queue.get()
            try:
                await _handle_one(r, topic, group, handler, message, consumer_name)
            except asyncio.CancelledError:
                raise
            except Exception:
                # _handle_one already swallows handler errors, so anything here is
                # a bug in the plumbing. Log and keep the worker alive: a silently
                # dead worker is permanent capacity loss that looks like a slow day.
                logger.exception("stream_worker_error", topic=topic)
            finally:
                queue.task_done()

    workers = [asyncio.create_task(_worker()) for _ in range(max(concurrency, 1))]
    # Immediately on startup, then time-based (busy batches would starve an
    # iteration-count cadence).
    next_reclaim_at = 0.0

    try:
        while True:
            if asyncio.get_event_loop().time() >= next_reclaim_at:
                next_reclaim_at = asyncio.get_event_loop().time() + 60
                try:
                    start_id = "0-0"
                    while True:
                        # Always require the idle threshold: claiming younger
                        # messages would steal work from live replicas.
                        claimed = await r.xautoclaim(
                            topic, group, consumer_name,
                            min_idle_time=STALE_CLAIM_IDLE_MS,
                            start_id=start_id, count=batch_size,
                        )
                        # redis-py returns (next_start, messages[, deleted])
                        next_id = claimed[0]
                        messages = claimed[1] if len(claimed) > 1 else []
                        if messages:
                            logger.info(
                                "stale_messages_reclaimed", topic=topic, count=len(messages)
                            )
                            for message in messages:
                                await queue.put(message)
                        if not messages or str(next_id) in ("0-0", "b'0-0'"):
                            break
                        start_id = next_id
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.exception("xautoclaim_failed", topic=topic)

            try:
                entries = await r.xreadgroup(
                    group, consumer_name, {topic: ">"}, count=batch_size, block=block_ms
                )
            except asyncio.CancelledError:
                raise
            except aioredis.TimeoutError:
                # Benign: redis-py's client-side read timeout races the server's
                # BLOCK expiry on idle streams. No data either way — just re-poll.
                continue
            except Exception:
                logger.exception("stream_read_failed", topic=topic, retry_in_s=5)
                await asyncio.sleep(5)
                continue

            if not entries:
                continue

            for _stream, messages in entries:
                for message in messages:
                    # Blocks while every worker is busy, which IS the backpressure:
                    # at most ~2x concurrency messages sit in Redis's pending list,
                    # so a crash strands a small bounded set for XAUTOCLAIM rather
                    # than a whole batch.
                    await queue.put(message)
    finally:
        for w in workers:
            w.cancel()


async def _deliveries(r, topic: str, group: str, entry_id) -> int:
    """How many times this entry has been delivered; 1 when Redis cannot say."""
    try:
        rows = await r.xpending_range(topic, group, min=entry_id, max=entry_id, count=1)
        return int(rows[0]["times_delivered"]) if rows else 1
    except Exception:  # noqa: BLE001 — not knowing is not a reason to drop it
        return 1


async def _heartbeat(r, topic: str, group: str, consumer_name: str, entry_id) -> None:
    """Renew our claim on a long-running message. JUSTID resets the idle clock
    without counting as a delivery."""
    while True:
        await asyncio.sleep(HEARTBEAT_S)
        try:
            await r.xclaim(topic, group, consumer_name, min_idle_time=0, message_ids=[entry_id], justid=True)
        except Exception:  # noqa: BLE001 — a missed heartbeat is the old behaviour, not a failure
            pass


async def _dead_letter(r, topic: str, group: str, entry_id, fields: dict, exc: Exception) -> None:
    """Preserve a permanently failed payload for inspection and replay."""
    deliveries = await _deliveries(r, topic, group, entry_id)
    try:
        await r.xadd(
            f"{topic}.dead",
            {
                "data": (fields or {}).get("data", ""),
                "entry_id": str(entry_id),
                "deliveries": str(deliveries),
                "error": f"{type(exc).__name__}: {exc}"[:500],
            },
            maxlen=1000,
            approximate=True,
        )
    except Exception:  # noqa: BLE001
        logger.exception("dead_letter_failed", topic=topic, entry_id=entry_id)


async def _handle_one(r, topic: str, group: str, handler, message, consumer_name: str = "") -> None:
    entry_id, fields = message
    beat = asyncio.create_task(_heartbeat(r, topic, group, consumer_name, entry_id)) if consumer_name else None
    try:
        payload = json.loads(fields["data"])
        await handler(payload)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        if _is_transient(exc):
            # Infrastructure is down, not the message: leave it pending so
            # XAUTOCLAIM redelivers it, and slow down instead of burning the
            # queue (a DB outage once acked-and-dropped 885 messages here).
            logger.warning(
                "handler_transient_error", topic=topic, entry_id=entry_id, error=str(exc)[:200]
            )
            await asyncio.sleep(5)
            return
        logger.exception(
            "handler_failed",
            topic=topic,
            entry_id=entry_id,
            payload=(fields or {}).get("data", "")[:500],
        )
        await _dead_letter(r, topic, group, entry_id, fields, exc)
    finally:
        if beat:
            beat.cancel()
    await r.xack(topic, group, entry_id)


def _is_transient(exc: BaseException | None) -> bool:
    """Connection-level failures anywhere in the exception chain."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if isinstance(exc, (ConnectionError, OSError, TimeoutError)):
            return True
        if getattr(exc, "connection_invalidated", False):  # sqlalchemy DBAPIError
            return True
        if "connect" in type(exc).__name__.lower():  # asyncpg/redis *Connection* errors
            return True
        exc = exc.__cause__ or exc.__context__
    return False
