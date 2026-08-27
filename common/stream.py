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


async def publish(topic: str, message: dict) -> str:
    """Publish a JSON message to a topic. Returns the stream entry id."""
    r = get_redis()
    entry_id = await r.xadd(
        topic, {"data": json.dumps(message, default=str)},
        maxlen=STREAM_MAXLEN, approximate=True,
    )
    return entry_id


STALE_CLAIM_IDLE_MS = 300_000  # reclaim messages a dead consumer held > 5 min


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

    Failed messages are logged and acked (recorded, not retried forever) —
    the DB keeps the authoritative state, so a stage can be re-driven from
    persisted rows; poison messages must not wedge the stream. Messages
    stranded in a dead consumer's pending list (e.g. after a restart under
    a different consumer name) are reclaimed via XAUTOCLAIM.

    concurrency > 1 processes a batch's messages in parallel — safe only
    for handlers whose items are independent (classification, enrichment);
    correlation must stay at 1 or concurrent articles for the same real
    event would race the match-or-create and split the cluster.
    """
    r = get_redis()
    try:
        await r.xgroup_create(topic, group, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    logger.info("consumer_started", topic=topic, group=group, consumer=consumer_name)
    next_reclaim_at = 0.0  # immediately on startup, then time-based (busy
    # batches would starve an iteration-count cadence)
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
                        logger.info("stale_messages_reclaimed", topic=topic, count=len(messages))
                        await _process(r, topic, group, handler, messages, concurrency)
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
            await _process(r, topic, group, handler, messages, concurrency)


async def _process(r, topic: str, group: str, handler, messages, concurrency: int = 1) -> None:
    if concurrency <= 1 or len(messages) <= 1:
        for message in messages:
            await _handle_one(r, topic, group, handler, message)
        return
    semaphore = asyncio.Semaphore(concurrency)

    async def bounded(message):
        async with semaphore:
            await _handle_one(r, topic, group, handler, message)

    await asyncio.gather(*(bounded(m) for m in messages))


async def _handle_one(r, topic: str, group: str, handler, message) -> None:
    entry_id, fields = message
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
