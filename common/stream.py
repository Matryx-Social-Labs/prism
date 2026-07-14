"""Streaming spine — Redis Streams for the prototype.

Every stage is a consumer of one topic and a producer to the next
(ARCHITECTURE.md "stream, not batch"). This module is the only place that
talks to the broker, so swapping Redis Streams for Kafka/Redpanda/NATS
later means reimplementing publish/consume, not touching stage logic.
"""

import asyncio
import json
import logging
from collections.abc import Awaitable, Callable

import redis.asyncio as aioredis

from common.config import get_settings

logger = logging.getLogger(__name__)

# Topics per docs/DB-SCHEMA.md (feed.updates deferred with real personalization)
RAW_ITEMS = "raw.items"
CLASSIFIED_ITEMS = "classified.items"
ENRICHED_ITEMS = "enriched.items"
EVENTS = "events"
EVENT_UPDATES = "event.updates"

_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(
            get_settings().redis_url,
            decode_responses=True,
            socket_connect_timeout=10,
            socket_keepalive=True,
            retry_on_timeout=True,
            health_check_interval=30,
        )
    return _redis


async def publish(topic: str, message: dict) -> str:
    """Publish a JSON message to a topic. Returns the stream entry id."""
    r = get_redis()
    entry_id = await r.xadd(topic, {"data": json.dumps(message, default=str)})
    return entry_id


STALE_CLAIM_IDLE_MS = 300_000  # reclaim messages a dead consumer held > 5 min


async def consume(
    topic: str,
    group: str,
    handler: Callable[[dict], Awaitable[None]],
    consumer_name: str = "worker-1",
    block_ms: int = 5000,
    batch_size: int = 10,
) -> None:
    """Consume a topic forever with a consumer group.

    Failed messages are logged and acked (recorded, not retried forever) —
    the DB keeps the authoritative state, so a stage can be re-driven from
    persisted rows; poison messages must not wedge the stream. Messages
    stranded in a dead consumer's pending list (e.g. after a restart under
    a different consumer name) are reclaimed via XAUTOCLAIM.
    """
    r = get_redis()
    try:
        await r.xgroup_create(topic, group, id="0", mkstream=True)
    except aioredis.ResponseError as e:
        if "BUSYGROUP" not in str(e):
            raise

    logger.info("consuming topic=%s group=%s consumer=%s", topic, group, consumer_name)
    iterations = 0
    while True:
        # Reclaim stale pending messages on startup and periodically.
        if iterations % 12 == 0:
            try:
                # Always require the idle threshold: claiming younger messages
                # would steal work from live replicas mid-processing.
                claimed = await r.xautoclaim(
                    topic, group, consumer_name,
                    min_idle_time=STALE_CLAIM_IDLE_MS,
                    start_id="0-0", count=batch_size,
                )
                # redis-py returns (next_start, messages) or (next_start, messages, deleted)
                messages = claimed[1] if len(claimed) > 1 else []
                if messages:
                    logger.info("reclaimed %d stale messages topic=%s", len(messages), topic)
                    await _process(r, topic, group, handler, messages)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("xautoclaim failed topic=%s", topic)
        iterations += 1

        try:
            entries = await r.xreadgroup(
                group, consumer_name, {topic: ">"}, count=batch_size, block=block_ms
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("stream read failed topic=%s; retrying in 5s", topic)
            await asyncio.sleep(5)
            continue

        if not entries:
            continue

        for _stream, messages in entries:
            await _process(r, topic, group, handler, messages)


async def _process(r, topic: str, group: str, handler, messages) -> None:
    for entry_id, fields in messages:
        try:
            payload = json.loads(fields["data"])
            await handler(payload)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception(
                "handler failed topic=%s entry=%s payload=%s",
                topic,
                entry_id,
                (fields or {}).get("data", "")[:500],
            )
        finally:
            await r.xack(topic, group, entry_id)
