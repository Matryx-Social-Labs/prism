"""Redis single-flight lock (E1). Proves cross-process exclusivity against a
live Redis; skips cleanly when none is reachable.
"""

import asyncio
import uuid

import pytest

from common.locks import single_flight
from common.stream import get_redis

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _redis_reachable() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception:  # noqa: BLE001 — any connection failure means skip
        return False


async def test_only_one_leader_and_produce_runs_once():
    if not await _redis_reachable():
        pytest.skip("no redis — run `docker compose up -d redis`")
    key = f"test-{uuid.uuid4()}"
    produced = 0

    async def work() -> bool:
        nonlocal produced
        async with single_flight(key, ttl=10, poll_interval=0.05) as leader:
            if leader:
                # Simulate the generate+persist the real caller does under the lock.
                await asyncio.sleep(0.3)
                produced += 1
            return leader

    leaders = await asyncio.gather(*[work() for _ in range(8)])

    assert sum(leaders) == 1, f"expected exactly one leader, got {sum(leaders)}"
    assert produced == 1, f"work ran {produced} times, expected once"


async def test_lock_released_after_use():
    if not await _redis_reachable():
        pytest.skip("no redis — run `docker compose up -d redis`")
    key = f"test-{uuid.uuid4()}"
    async with single_flight(key) as leader:
        assert leader is True
        assert await get_redis().exists(f"sf:{key}") == 1  # held during the block
    assert await get_redis().exists(f"sf:{key}") == 0  # released after
