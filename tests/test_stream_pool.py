"""One slow message must not idle every other worker.

The consumer used to read a batch, gather() all of it, and only read the next
batch once EVERY message had finished. With enrichment's batch_size == concurrency
== 12 the semaphore bounded nothing and throughput became
`batch_size / slowest-of-the-batch` instead of `concurrency / mean`.

That is worth a test rather than a comment because it is INVISIBLE in production:
nothing errors, no message is lost, the queue just drains slower than the maths
says it should. It went unnoticed long enough for 1,023 relevant articles to be
collected, paid for, and never enriched.
"""

import asyncio

import pytest

from common import stream

pytestmark = pytest.mark.asyncio


class FakeRedis:
    """Just enough Redis for `consume`: hand out messages once, record acks."""

    def __init__(self, messages: list[tuple[str, dict]]):
        self._to_deliver = list(messages)
        self.acked: list[str] = []

    async def xgroup_create(self, *a, **kw):
        return True

    async def xautoclaim(self, *a, **kw):
        return ("0-0", [])

    async def xreadgroup(self, group, consumer, streams, count=10, block=0):
        if not self._to_deliver:
            await asyncio.sleep(0.01)   # idle stream: let the loop breathe
            return []
        batch, self._to_deliver = self._to_deliver[:count], self._to_deliver[count:]
        return [("topic", batch)]

    async def xack(self, topic, group, entry_id):
        self.acked.append(entry_id)


async def _run(handler, messages, concurrency, monkeypatch, timeout=2.0):
    fake = FakeRedis(messages)
    monkeypatch.setattr(stream, "get_redis", lambda: fake)
    task = asyncio.create_task(
        stream.consume("topic", "g", handler, concurrency=concurrency,
                       batch_size=len(messages), block_ms=1)
    )
    try:
        await asyncio.wait_for(asyncio.shield(_drain(fake, len(messages))), timeout)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    return fake


async def _drain(fake, n):
    while len(fake.acked) < n:
        await asyncio.sleep(0.005)


def _msgs(n):
    import json
    return [(f"{i}-0", {"data": json.dumps({"n": i})}) for i in range(n)]


async def test_a_slow_message_does_not_stall_the_messages_behind_it(monkeypatch):
    """THE REGRESSION, and it only shows across BATCH BOUNDARIES.

    A first attempt at this test used a single batch, where one straggler among
    four with four slots looks identical under either design — and the mutation
    (restoring the gather-the-batch barrier) passed. The defect is that the next
    READ waited for the current batch to fully drain, so it needs a second batch
    to be observable at all.

    Eight messages, four at a time, four workers. Message 0 blocks forever. The
    rest of its batch AND the whole second batch must still get through; under
    the old shape messages 4-7 were never even read.
    """
    started = asyncio.Event()
    release = asyncio.Event()
    done: list[int] = []

    async def handler(payload):
        if payload["n"] == 0:
            started.set()
            await release.wait()
        done.append(payload["n"])

    fake = FakeRedis(_msgs(8))
    monkeypatch.setattr(stream, "get_redis", lambda: fake)
    task = asyncio.create_task(
        stream.consume("topic", "g", handler, concurrency=4, batch_size=4, block_ms=1)
    )
    try:
        await asyncio.wait_for(started.wait(), 2)
        for _ in range(400):
            if sorted(done) == [1, 2, 3, 4, 5, 6, 7]:
                break
            await asyncio.sleep(0.005)
        assert sorted(done) == [1, 2, 3, 4, 5, 6, 7], (
            f"expected everything but the blocked message to finish; got {sorted(done)} — "
            "the batch barrier is back and the second batch is never read"
        )
        assert 0 not in done
    finally:
        release.set()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task


async def test_every_message_is_acked_exactly_once(monkeypatch):
    """The pool must not drop or double-handle work."""
    seen: list[int] = []

    async def handler(payload):
        seen.append(payload["n"])

    fake = await _run(handler, _msgs(12), 4, monkeypatch)
    assert sorted(seen) == list(range(12))
    assert len(fake.acked) == 12 and len(set(fake.acked)) == 12


async def test_concurrency_one_stays_strictly_sequential(monkeypatch):
    """Correlation depends on this: two articles for the same real event must not
    race match-or-create, or the cluster splits."""
    overlap = 0
    inside = 0

    async def handler(payload):
        nonlocal overlap, inside
        inside += 1
        overlap = max(overlap, inside)
        await asyncio.sleep(0.01)
        inside -= 1

    await _run(handler, _msgs(6), 1, monkeypatch)
    assert overlap == 1, f"{overlap} handlers ran at once at concurrency=1"


async def test_a_failing_handler_does_not_kill_its_worker(monkeypatch):
    """A poison message must cost one message, not one worker. A silently dead
    worker is permanent capacity loss that looks exactly like a slow day."""
    handled: list[int] = []

    async def handler(payload):
        if payload["n"] == 0:
            raise RuntimeError("poison")
        handled.append(payload["n"])

    fake = await _run(handler, _msgs(5), 1, monkeypatch)
    assert sorted(handled) == [1, 2, 3, 4]
    assert len(fake.acked) == 5      # the poison message is acked, not retried forever


async def test_a_message_delivered_too_often_is_dead_lettered_and_acked(monkeypatch):
    """Poison is not unlucky: past MAX_DELIVERIES the entry goes to <topic>.dead
    with its payload and the stream moves on."""
    class Fake(FakeRedis):
        def __init__(self, messages):
            super().__init__(messages)
            self.dead = []
        async def xpending_range(self, topic, group, min, max, count):
            return [{"times_delivered": stream.MAX_DELIVERIES + 1}]
        async def xadd(self, topic, fields, **kw):
            self.dead.append((topic, fields))
    handled = []
    async def handler(p):
        handled.append(p)
    fake = Fake(_msgs(1))
    monkeypatch.setattr(stream, "get_redis", lambda: fake)
    task = asyncio.create_task(stream.consume("topic", "g", handler, concurrency=1, batch_size=1, block_ms=1))
    try:
        await asyncio.wait_for(asyncio.shield(_drain(fake, 1)), 2.0)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert handled == []
    assert fake.dead and fake.dead[0][0] == "topic.dead"
    assert fake.acked == ["0-0"]


async def test_a_long_handler_renews_its_claim(monkeypatch):
    """While a handler runs past the idle threshold its message must not look
    abandoned: the heartbeat XCLAIMs it (JUSTID) on an interval."""
    class Fake(FakeRedis):
        def __init__(self, messages):
            super().__init__(messages)
            self.claims = []
        async def xpending_range(self, *a, **kw):
            return [{"times_delivered": 1}]
        async def xclaim(self, topic, group, consumer, min_idle_time, message_ids, justid):
            self.claims.append((message_ids, justid))
    monkeypatch.setattr(stream, "HEARTBEAT_S", 0.02)
    async def slow(p):
        await asyncio.sleep(0.1)
    fake = Fake(_msgs(1))
    monkeypatch.setattr(stream, "get_redis", lambda: fake)
    task = asyncio.create_task(stream.consume("topic", "g", slow, consumer_name="w1", concurrency=1, batch_size=1, block_ms=1))
    try:
        await asyncio.wait_for(asyncio.shield(_drain(fake, 1)), 2.0)
    finally:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    assert len(fake.claims) >= 2 and all(j is True for _, j in fake.claims)
