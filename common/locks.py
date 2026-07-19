"""Cross-process single-flight lock over Redis.

The on-demand lens-brief endpoint must generate each (event, lens) at most once
even when a burst of viewers hits it — otherwise a popular story costs many LLM
calls instead of one (and, once the paywall lands, many sample decrements).

The previous in-process `asyncio.Lock` only single-flights within ONE API
process; on Railway with >1 replica (or the API racing the worker), each replica
still generates. This lock lives in Redis, which every replica shares, so the
guarantee holds fleet-wide.

Semantics: exactly one concurrent caller for a key acquires the lock and is told
to do the work (`leader=True`); the others wait for it to finish and are told to
re-read the shared cache (`leader=False`). If the leader takes longer than
`wait_timeout` or dies, a waiter falls back to `leader=True` so the request still
completes rather than hanging — correctness over strict single-flight.
"""

import asyncio
import secrets
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from common.stream import get_redis

# Release only if we still hold the lock (our token matches) — never delete a
# lock a slower run has since re-acquired.
_RELEASE = "if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) else return 0 end"


@asynccontextmanager
async def single_flight(
    key: str,
    *,
    ttl: int = 30,
    wait_timeout: float = 25.0,
    poll_interval: float = 0.2,
) -> AsyncIterator[bool]:
    """Yield True to the one caller that should produce the value, False to callers
    that waited for the producer (they should read the shared cache)."""
    redis = get_redis()
    lock_key = f"sf:{key}"
    token = secrets.token_hex(16)

    acquired = await redis.set(lock_key, token, nx=True, ex=ttl)
    if acquired:
        try:
            yield True
        finally:
            try:
                await redis.eval(_RELEASE, 1, lock_key, token)
            except Exception:  # noqa: BLE001 — TTL will reap the lock; never fail the request on release
                pass
        return

    # Waiter: poll until the holder releases (or we time out), then let the
    # caller re-read the cache. On timeout, fall back to producing ourselves.
    waited = 0.0
    while waited < wait_timeout:
        await asyncio.sleep(poll_interval)
        waited += poll_interval
        if not await redis.exists(lock_key):
            yield False
            return
    yield True  # holder stalled/died — produce rather than hang
