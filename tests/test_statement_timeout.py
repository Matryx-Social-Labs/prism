"""Worker statements run under a timeout, a cancelled one is retried rather than
dead-lettered, and migrations cannot queue every reader behind their DDL.

Every test here runs against the real test database: the point is what Postgres
and asyncpg actually raise, not what a hand-built exception looks like.
"""

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

from common import db, stream, timings
from common.config import get_settings
from tests.test_verified_tier import _db_reachable


@pytest.fixture
async def fresh_engine(monkeypatch):
    """A process with no engine yet, restored afterwards: the suite shares
    `common.db._engine`, and the default is read when the engine is built."""
    if not await _db_reachable():
        pytest.skip("no database")
    await db.get_engine().dispose()
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_session_factory", None)
    monkeypatch.setattr(db, "_default_statement_timeout", None)
    yield
    if db._engine is not None:
        await db._engine.dispose()


async def _cancelled_statement(monkeypatch) -> tuple[BaseException, list[str]]:
    counted: list[str] = []

    async def count(name: str, n: int = 1) -> None:
        counted.append(name)

    monkeypatch.setattr(timings, "count", count)
    with pytest.raises(DBAPIError) as caught:
        async with db.session_scope(statement_timeout="50ms") as s:
            await s.execute(text("SELECT pg_sleep(1)"))
    return caught.value, counted


async def test_the_process_default_reaches_every_pooled_connection(fresh_engine):
    # Arrange
    db.set_default_statement_timeout("7s")
    engine = db.get_engine()

    # Act: two connections held at once, so they are two distinct pool members
    async with engine.connect() as a, engine.connect() as b:
        seen = {
            (await a.execute(text("SHOW statement_timeout"))).scalar(),
            (await b.execute(text("SHOW statement_timeout"))).scalar(),
        }

    # Assert
    assert seen == {"7s"}


async def test_the_api_request_timeout_still_overrides_the_default(fresh_engine):
    db.set_default_statement_timeout("7s")
    gen = db.get_db()
    session = await anext(gen)
    try:
        assert (await session.execute(text("SHOW statement_timeout"))).scalar() == db.API_STATEMENT_TIMEOUT
    finally:
        await gen.aclose()


async def test_setting_the_default_after_the_engine_exists_raises(fresh_engine):
    db.get_engine()
    with pytest.raises(RuntimeError):
        db.set_default_statement_timeout("120s")


@pytest.mark.parametrize("value", ["120 s", "1s'; DROP TABLE x; --", "", "s", "5sec", "-1", "120", "00"])
def test_a_startup_timeout_that_is_not_a_plain_duration_fails_at_boot(value, monkeypatch):
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_default_statement_timeout", None)
    with pytest.raises(ValueError):
        db.set_default_statement_timeout(value)


@pytest.mark.parametrize("value", ["0", "250ms", "120s", "10min", "1h"])
def test_a_startup_timeout_needs_a_unit_or_is_exactly_zero(value, monkeypatch):
    """REGRESSION: a unitless number is milliseconds to Postgres, so `120` meant
    every worker statement cancelled after 120 ms."""
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_default_statement_timeout", None)
    db.set_default_statement_timeout(value)
    assert db.server_settings() == {"statement_timeout": value}


@pytest.mark.parametrize("value", ["1s'; DROP TABLE x; --", "5sec", "-1"])
async def test_a_scope_override_is_bound_and_validated_by_postgres(value, fresh_engine):
    with pytest.raises(DBAPIError):
        async with db.session_scope(statement_timeout=value):
            pass


async def test_a_scope_override_cancels_a_long_statement_and_is_counted(fresh_engine, monkeypatch):
    # Act
    exc, counted = await _cancelled_statement(monkeypatch)

    # Assert
    assert db.sqlstate_in_chain(exc, {db.QUERY_CANCELED})
    assert counted == ["db.statement_timeout"]


class _Redis:
    """Just enough of a stream for _handle_one: delivery count, per-entry counters,
    ack, dead letter. `broken` fails every counter write."""

    def __init__(self, delivered: int = 1, broken: bool = False):
        self.delivered, self.broken = delivered, broken
        self.acked, self.dead, self.counts, self._queued = [], [], {}, []

    async def xpending_range(self, topic, group, min, max, count):
        return [{"times_delivered": self.delivered}]

    async def xadd(self, topic, fields, **kw):
        self.dead.append(topic)

    async def xack(self, topic, group, entry_id):
        self.acked.append(entry_id)

    def pipeline(self, transaction=False):
        return self

    def incr(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1
        self._queued.append(self.counts[key])

    def expire(self, key, ttl):
        self._queued.append(True)

    async def execute(self):
        out, self._queued = self._queued, []
        if self.broken:
            raise ConnectionError("redis down")
        return out


async def _handle(exc: BaseException, r: _Redis, monkeypatch) -> list[str]:
    counted: list[str] = []

    async def count(name: str, n: int = 1) -> None:
        counted.append(name)

    async def no_sleep(_s):
        pass

    async def handler(payload):
        raise exc

    monkeypatch.setattr(timings, "count", count)
    monkeypatch.setattr(stream.asyncio, "sleep", no_sleep)
    await stream._handle_one(r, "t", "g", handler, ("1-1", {"data": '{"raw_item_id": "x"}'}))
    return counted


async def test_a_statement_that_keeps_timing_out_is_dead_lettered_on_its_last_timeout(fresh_engine, monkeypatch):
    # Arrange
    exc, _ = await _cancelled_statement(monkeypatch)
    r = _Redis()

    # Act: the same entry times out on each delivery
    for _ in range(stream.STATEMENT_TIMEOUTS_BEFORE_DEAD - 1):
        await _handle(exc, r, monkeypatch)
        assert r.acked == [] and r.dead == [], "dead-lettered before its last timeout"
    counted = await _handle(exc, r, monkeypatch)

    # Assert
    assert r.acked == ["1-1"] and r.dead == ["t.dead"]
    assert "dead.t.statement_timeout" in counted


async def test_deliveries_for_other_reasons_do_not_count_as_timeouts(fresh_engine, monkeypatch):
    """REGRESSION: a message reclaimed twice (a deploy, a connection error) was
    dead-lettered on its FIRST timeout, because the cap counted deliveries."""
    exc, _ = await _cancelled_statement(monkeypatch)
    r = _Redis(delivered=stream.STATEMENT_TIMEOUTS_BEFORE_DEAD)
    await _handle(exc, r, monkeypatch)
    assert r.acked == [] and r.dead == []


async def test_a_timeout_redis_cannot_count_is_left_pending(fresh_engine, monkeypatch):
    exc, _ = await _cancelled_statement(monkeypatch)
    r = _Redis(delivered=50, broken=True)
    for _ in range(stream.STATEMENT_TIMEOUTS_BEFORE_DEAD + 1):
        await _handle(exc, r, monkeypatch)
    assert r.acked == [] and r.dead == []


async def test_a_connection_error_never_dead_letters(monkeypatch):
    r = _Redis(delivered=50)
    await _handle(ConnectionError("db away"), r, monkeypatch)
    assert r.acked == [] and r.dead == []


async def test_an_ordinary_failure_is_still_permanent(fresh_engine):
    with pytest.raises(IntegrityError) as caught:
        async with db.session_scope() as s:
            await s.execute(text("CREATE TEMP TABLE t_once (id int PRIMARY KEY)"))
            await s.execute(text("INSERT INTO t_once VALUES (1), (1)"))
    assert not stream._is_transient(caught.value)
    assert not stream._is_transient(ValueError("bad payload"))


@pytest.mark.parametrize(("env", "expected"), [(None, "5s"), ("", "5s"), ("3s", "3s")])
async def test_migrations_connect_under_a_lock_timeout(env, expected, monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    if env is None:
        monkeypatch.delenv("PRISM_MIGRATION_LOCK_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("PRISM_MIGRATION_LOCK_TIMEOUT", env)
    # The same connect_args db/env.py hands alembic's engine.
    engine = create_async_engine(
        get_settings().database_url, poolclass=NullPool, connect_args=db.migration_connect_args()
    )
    try:
        async with engine.connect() as conn:
            assert (await conn.execute(text("SHOW lock_timeout"))).scalar() == expected
    finally:
        await engine.dispose()


class _StopMain(Exception):
    """Raised by the log line after the call, so `main` stops before it starts any task."""


def _stop(*_a, **_k):
    raise _StopMain


@pytest.mark.parametrize(("env", "expected"), [(None, "120s"), ("45s", "45s"), ("", "120s")])
async def test_worker_startup_sets_the_statement_timeout(monkeypatch, env, expected):
    # Arrange: record the call; the startup log line right after it stops main
    from types import SimpleNamespace

    from worker import __main__ as worker_main

    seen: list[str] = []
    monkeypatch.setattr(worker_main, "set_default_statement_timeout", seen.append)
    monkeypatch.setattr(worker_main, "logger", SimpleNamespace(info=_stop))
    if env is None:
        monkeypatch.delenv("PRISM_WORKER_STATEMENT_TIMEOUT", raising=False)
    else:
        monkeypatch.setenv("PRISM_WORKER_STATEMENT_TIMEOUT", env)

    # Act
    with pytest.raises(_StopMain):
        await worker_main.main(["correlation"])

    # Assert
    assert seen == [expected]


# ── advisory-lock waits ──

@pytest.mark.parametrize(("key", "tool_sql"), [
    # Each key as the worker passes it, and the lock a tool takes with its own SQL:
    # a changed key would silently stop the two excluding each other.
    ("correlation.match_or_create", "SELECT pg_advisory_xact_lock(hashtext('correlation.match_or_create'))"),
    ("stories.assign", "SELECT pg_advisory_xact_lock(hashtext('stories.assign'))"),
    (0x50415254, "SELECT pg_advisory_xact_lock(1346458196)"),  # correlation/partition._PARTITION_LOCK_KEY
])
async def test_waiting_for_a_lock_outlives_the_statement_timeout_and_restores_it(key, tool_sql, fresh_engine,
                                                                                  monkeypatch):
    """REGRESSION: the worker runs with a statement_timeout; a tool holding the lock
    for longer must not get the wait cancelled (and the message dead-lettered).
    The override comes back for everything after the lock."""
    import asyncio
    import time

    async def nothing(*_a, **_k):
        return None

    monkeypatch.setattr(timings, "count", nothing)  # session_scope counts the cancel
    held = asyncio.Event()

    async def hold() -> None:
        async with db.session_scope() as other:
            await other.execute(text(tool_sql))
            held.set()
            await asyncio.sleep(0.3)

    holder = asyncio.create_task(hold())
    await held.wait()
    seen: dict = {}
    with pytest.raises(DBAPIError) as caught:
        async with db.session_scope(statement_timeout="50ms") as s:
            started = time.perf_counter()
            await db.wait_for_xact_lock(s, key)
            seen["wait_ms"] = (time.perf_counter() - started) * 1000
            seen["timeout"] = (await s.execute(text("SHOW statement_timeout"))).scalar()
            await s.execute(text("SELECT pg_sleep(1)"))
    await holder
    assert seen["wait_ms"] >= 200, "the wait ran past the 50ms timeout: it waited on the tool's lock"
    assert seen["timeout"] == "50ms"
    assert db.sqlstate_in_chain(caught.value, {db.QUERY_CANCELED}), "a slow query after the lock is still cancelled"


async def test_the_variant_fold_waits_out_the_match_lock_on_its_own_connection(fresh_engine):
    """correlation/variants takes the match lock on a raw asyncpg connection, which
    carries the worker's statement_timeout too."""
    import asyncio
    import time

    from correlation import variants

    db.set_default_statement_timeout("50ms")
    held = asyncio.Event()

    async def hold() -> None:
        async with db.session_scope() as other:
            await other.execute(text("SELECT pg_advisory_xact_lock(hashtext('correlation.match_or_create'))"))
            held.set()
            await asyncio.sleep(0.3)

    holder = asyncio.create_task(hold())
    await held.wait()
    c = await variants.connect()
    try:
        started = time.perf_counter()
        assert await variants.settle(c, [], {}, via="test", fold=False) == []
        waited_ms = (time.perf_counter() - started) * 1000
        timeout = await c.fetchval("SHOW statement_timeout")
    finally:
        await c.close()
        await holder
    assert waited_ms >= 200 and timeout == "50ms"


def test_no_worker_module_waits_on_an_advisory_lock_but_through_the_helper():
    import inspect

    from correlation import consumer, partition, stories, story_merge

    for module in (consumer, stories, story_merge, partition):
        assert "pg_advisory_xact_lock" not in inspect.getsource(module), module.__name__


# ── the interval reconcilers ──

class _Stop(Exception):
    pass


def _scope_recorder(seen: list, stop_after: int):
    """A session_scope that records its timeout and fails on entry; the
    `stop_after`-th entry cancels, which no `except Exception` loop swallows."""
    import asyncio
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def scope(statement_timeout=None):
        seen.append(statement_timeout)
        raise asyncio.CancelledError if len(seen) >= stop_after else _Stop
        yield

    return scope


async def test_the_trending_pass_runs_under_the_reconciler_timeout(monkeypatch):
    import asyncio

    from worker import __main__ as worker_main

    seen: list = []
    monkeypatch.setattr(db, "session_scope", _scope_recorder(seen, stop_after=2))
    monkeypatch.setattr(worker_main, "TRENDING_INTERVAL_S", 0)
    with pytest.raises(asyncio.CancelledError):
        await worker_main._trending_reconciler()
    assert seen == [db.RECONCILER_STATEMENT_TIMEOUT] * 2


async def test_the_partition_graph_load_runs_under_the_reconciler_timeout(monkeypatch):
    from correlation import partition

    seen: list = []
    monkeypatch.setattr(partition, "session_scope", _scope_recorder(seen, stop_after=99))
    with pytest.raises(_Stop):
        await partition.compute_partition()
    assert seen == [db.RECONCILER_STATEMENT_TIMEOUT]


async def test_a_worker_timeout_switched_off_is_not_capped_by_an_override(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    monkeypatch.setattr(db, "_default_statement_timeout", "0")
    async with db.session_scope(statement_timeout="50ms") as s:
        shown = (await s.execute(text("SHOW statement_timeout"))).scalar()
    assert shown != "50ms"
