"""The markets digest never makes a reader wait for the model (correlation/digest.py).

It is an LLM summary cached for three hours. On 2026-09-27 the first request
after expiry waited 27 s while it was regenerated inside the request. Now an
expired digest is served at once and one refresh runs behind it; only an empty
cache (first ever, or a day unread) generates in the request.
"""

import asyncio
import json
import time
import uuid

import pytest
import pytest_asyncio

from common.stream import get_redis
from correlation import digest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _redis_up() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest_asyncio.fixture(loop_scope="session")
async def key(monkeypatch):
    if not await _redis_up():
        pytest.skip("no redis")
    k = f"test:digest:{uuid.uuid4().hex[:8]}"
    monkeypatch.setattr(digest, "CACHE_KEY", k)
    yield k
    await get_redis().delete(k, f"refresh:{k}", f"sf:{k}")


def _counting(result: dict | None, delay: float = 0.0):
    calls: list[float] = []

    async def fake() -> dict | None:
        calls.append(time.time())
        await asyncio.sleep(delay)
        return result

    return fake, calls


async def _settle():
    await asyncio.gather(*list(digest._refreshing))


async def test_an_expired_digest_is_served_at_once_and_refreshed_behind_it(key, monkeypatch):
    await get_redis().set(key, json.dumps({"digest": {"summary": "old"}, "fresh_until": time.time() - 1}))
    fake, calls = _counting({"summary": "new"}, delay=0.5)
    monkeypatch.setattr(digest, "_generate", fake)

    t = time.perf_counter()
    got = await digest.get_market_digest()
    assert time.perf_counter() - t < 0.3, "the reader waited for the model"
    assert got == {"summary": "old"}

    await _settle()
    assert len(calls) == 1
    assert await digest.get_market_digest() == {"summary": "new"}


async def test_a_fresh_digest_never_calls_the_model(key, monkeypatch):
    await get_redis().set(key, json.dumps({"digest": {"summary": "fresh"}, "fresh_until": time.time() + 600}))
    fake, calls = _counting({"summary": "new"})
    monkeypatch.setattr(digest, "_generate", fake)
    assert await digest.get_market_digest() == {"summary": "fresh"}
    await _settle()
    assert calls == []


async def test_many_readers_of_an_expired_digest_start_one_refresh(key, monkeypatch):
    await get_redis().set(key, json.dumps({"digest": {"summary": "old"}, "fresh_until": time.time() - 1}))
    fake, calls = _counting({"summary": "new"}, delay=0.3)
    monkeypatch.setattr(digest, "_generate", fake)
    await asyncio.gather(*(digest.get_market_digest() for _ in range(5)))
    await _settle()
    assert len(calls) == 1


async def test_a_failed_refresh_keeps_the_old_digest(key, monkeypatch):
    await get_redis().set(key, json.dumps({"digest": {"summary": "old"}, "fresh_until": time.time() - 1}))
    fake, _ = _counting(None)
    monkeypatch.setattr(digest, "_generate", fake)
    await digest.get_market_digest()
    await _settle()
    assert await digest.get_market_digest() == {"summary": "old"}


async def test_a_digest_cached_before_this_change_still_reads(key, monkeypatch):
    """Production holds a bare digest under the key until it expires."""
    await get_redis().set(key, json.dumps({"summary": "legacy"}))
    fake, calls = _counting({"summary": "new"})
    monkeypatch.setattr(digest, "_generate", fake)
    assert await digest.get_market_digest() == {"summary": "legacy"}
    await _settle()
    assert len(calls) == 1, "a bare digest has no freshness stamp, so it is refreshed"


async def test_an_empty_cache_still_generates_in_the_request(key, monkeypatch):
    fake, calls = _counting({"summary": "first"})
    monkeypatch.setattr(digest, "_generate", fake)
    assert await digest.get_market_digest() == {"summary": "first"}
    assert len(calls) == 1
