"""A permanently failing item is retried a few times, then given up — not paid for forever.

requeue_stalled republishes, every 10 minutes, any item that never reached its
next stage. That is how the pipeline recovers from an outage, and it is right
for a transient failure (a timeout, a quota, the database away — none of which
dead-letters). But an article the model refuses, or answers with an invalid
record twice, dead-letters, is republished, is paid for and dead-letters again,
every 10 minutes with no end (audit 2026-09-29). Counting only DEAD LETTERS per
item keeps an outage from ever giving up on good items.
"""

import datetime as dt
import json
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import text

from common import stream
from common.db import session_scope
from ingestion import runner

pytestmark = pytest.mark.asyncio(loop_scope="session")


class _Pipe:
    def __init__(self, store):
        self.store, self.ops = store, []

    def incr(self, key):
        self.ops.append(("incr", key))

    def expire(self, key, seconds):
        self.ops.append(("expire", key, seconds))

    async def execute(self):
        for op in self.ops:
            if op[0] == "incr":
                self.store[op[1]] = self.store.get(op[1], 0) + 1


class _Redis:
    def __init__(self):
        self.store, self.dead = {}, []

    def pipeline(self, transaction=False):
        return _Pipe(self.store)

    async def xadd(self, topic, fields, **kw):
        self.dead.append((topic, fields))

    async def xpending_range(self, *a, **kw):
        return [{"times_delivered": 1}]

    async def mget(self, keys):
        return [self.store.get(k) for k in keys]


async def test_a_dead_letter_counts_against_its_item(monkeypatch):
    r = _Redis()
    monkeypatch.setattr(stream, "get_redis", lambda: r)
    raw = str(uuid.uuid4())
    fields = {"data": json.dumps({"raw_item_id": raw})}
    for _ in range(2):
        await stream._dead_letter(r, "classified.items", "enrichment", "1-0", fields, ValueError("invalid record"))
    assert await stream.permanent_failures([raw, str(uuid.uuid4())]) == {raw: 2}


async def test_a_payload_without_an_item_is_not_counted(monkeypatch):
    r = _Redis()
    await stream._dead_letter(r, "admin.triggers", "worker", "1-0", {"data": "{}"}, ValueError("x"))
    await stream._dead_letter(r, "admin.triggers", "worker", "1-0", {"data": "not json"}, ValueError("x"))
    assert r.store == {} and len(r.dead) == 2


async def _db() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:  # noqa: BLE001
        return False


@pytest_asyncio.fixture(loop_scope="session")
async def stalled():
    """Two relevant items that never got an article, stalled for an hour."""
    if not await _db():
        pytest.skip("no database")
    src, ids = uuid.uuid4(), [uuid.uuid4(), uuid.uuid4()]
    hour_ago = dt.datetime.now(dt.UTC) - dt.timedelta(hours=1)
    async with session_scope() as s:
        await s.execute(text("INSERT INTO sources (id, slug, name, source_type) VALUES (:i, :s, 'Requeue test', 'rss')"),
                        {"i": str(src), "s": f"requeue-{src.hex[:8]}"})
        for rid in ids:
            await s.execute(
                text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, created_at, updated_at) "
                     "VALUES (:i, :s, :e, :u, 't', '{}', 'relevant', :w, :w)"),
                {"i": str(rid), "s": str(src), "e": str(rid), "u": f"https://requeue.test/{rid}", "w": hour_ago},
            )
    yield ids
    async with session_scope() as s:
        await s.execute(text("DELETE FROM raw_items WHERE source_id = :s"), {"s": str(src)})
        await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(src)})


async def test_an_item_that_keeps_failing_is_given_up_and_the_rest_still_retried(monkeypatch, stalled):
    poison, flaky = stalled
    published, alerts = [], []

    async def publish(topic, message):
        published.append(message["raw_item_id"])

    async def failures(ids):
        return {str(poison): runner.MAX_PERMANENT_FAILURES, str(flaky): 1}

    async def notify(key, subject, body, **kw):
        alerts.append(subject)
        return True

    monkeypatch.setattr(runner.stream, "publish", publish)
    monkeypatch.setattr(runner.stream, "permanent_failures", failures)
    monkeypatch.setattr(runner.alerts, "notify", notify)
    await runner.requeue_stalled()

    assert str(flaky) in published
    assert str(poison) not in published
    async with session_scope() as s:
        row = (await s.execute(text("SELECT relevance, rejection_reason FROM raw_items WHERE id = :i"),
                               {"i": str(poison)})).one()
    assert row.relevance == "failed" and "permanent failures" in row.rejection_reason
    assert alerts, "a founder hears that items were given up"


async def test_without_the_failure_counts_nothing_is_given_up(monkeypatch, stalled):
    """Redis away is not evidence of failure: retry as before."""
    published = []

    async def publish(topic, message):
        published.append(message["raw_item_id"])

    async def failures(ids):
        raise ConnectionError("redis down")

    monkeypatch.setattr(runner.stream, "publish", publish)
    monkeypatch.setattr(runner.stream, "permanent_failures", failures)
    await runner.requeue_stalled()
    assert {str(i) for i in stalled} <= set(published)


async def test_many_failing_at_once_is_the_pipeline_and_nothing_is_given_up(monkeypatch, stalled):
    """Review 2026-09-29: a model answering every article with an invalid record
    (qwen, 2026-09-04) would have marked the whole backlog failed in 40 minutes."""
    published, alerts = [], []

    async def publish(topic, message):
        published.append(message["raw_item_id"])

    async def failures(ids):
        return {str(i): runner.MAX_PERMANENT_FAILURES for i in stalled}

    async def notify(key, subject, body, **kw):
        alerts.append(key)
        return True

    monkeypatch.setattr(runner, "SYSTEMIC_GIVE_UP", 1)
    monkeypatch.setattr(runner.stream, "publish", publish)
    monkeypatch.setattr(runner.stream, "permanent_failures", failures)
    monkeypatch.setattr(runner.alerts, "notify", notify)
    await runner.requeue_stalled()

    assert {str(i) for i in stalled} <= set(published)
    assert alerts == ["requeue-systemic"]
    async with session_scope() as s:
        states = (await s.execute(text("SELECT DISTINCT relevance FROM raw_items WHERE id = ANY(CAST(:i AS uuid[]))"),
                                  {"i": [str(i) for i in stalled]})).scalars().all()
    assert states == ["relevant"]
