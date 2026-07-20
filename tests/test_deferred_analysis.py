"""Deferred correlation analysis: the debounce + claim mechanics (no LLM).

Real-time attach marks an event dirty; the sweeper runs the expensive analysis
once, only after the debounce elapses. Verifies scheduling, due-filtering, the
NX leading-debounce, and single-claim.
"""

import time
import uuid

import pytest

from common.stream import get_redis
from correlation import consumer

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _redis_ok() -> bool:
    try:
        await get_redis().ping()
        return True
    except Exception:
        return False


async def test_debounce_due_filtering_and_claim(monkeypatch):
    if not await _redis_ok():
        pytest.skip("no redis")
    r = get_redis()
    await r.delete(consumer.DIRTY_KEY)

    claimed: list[str] = []

    async def fake_analyze(eid):
        claimed.append(str(eid))

    monkeypatch.setattr(consumer, "analyze_event_now", fake_analyze)

    e_future = uuid.uuid4()  # scheduled DEBOUNCE out — not yet due
    e_due = uuid.uuid4()  # forced past-due
    await consumer.mark_event_dirty(e_future)
    await r.zadd(consumer.DIRTY_KEY, {str(e_due): time.time() - 1})

    processed = await consumer.run_due_analyses()

    assert processed == 1
    assert str(e_due) in claimed and str(e_future) not in claimed  # only due one ran
    assert await r.zscore(consumer.DIRTY_KEY, str(e_due)) is None  # claimed + removed
    future_score = await r.zscore(consumer.DIRTY_KEY, str(e_future))
    assert future_score is not None  # still queued

    # NX leading debounce: re-marking an already-scheduled event doesn't move it.
    await consumer.mark_event_dirty(e_future)
    assert await r.zscore(consumer.DIRTY_KEY, str(e_future)) == future_score

    await r.delete(consumer.DIRTY_KEY)
