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


@pytest.mark.parametrize("value", ["120 s", "1s'; DROP TABLE x; --", "", "s", "5sec", "-1"])
def test_a_startup_timeout_that_is_not_a_plain_duration_fails_at_boot(value, monkeypatch):
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_default_statement_timeout", None)
    with pytest.raises(ValueError):
        db.set_default_statement_timeout(value)


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
    """Just enough of a stream for _handle_one: delivery count, ack, dead letter."""

    def __init__(self, delivered: int):
        self.delivered, self.acked, self.dead = delivered, [], []

    async def xpending_range(self, topic, group, min, max, count):
        return [{"times_delivered": self.delivered}]

    async def xadd(self, topic, fields, **kw):
        self.dead.append(topic)

    async def xack(self, topic, group, entry_id):
        self.acked.append(entry_id)

    def pipeline(self, transaction=False):
        return self

    def incr(self, key):
        pass

    def expire(self, key, ttl):
        pass

    async def execute(self):
        return []


async def _handle(exc: BaseException, delivered: int, monkeypatch) -> tuple[_Redis, list[str]]:
    counted: list[str] = []

    async def count(name: str, n: int = 1) -> None:
        counted.append(name)

    async def no_sleep(_s):
        pass

    async def handler(payload):
        raise exc

    monkeypatch.setattr(timings, "count", count)
    monkeypatch.setattr(stream.asyncio, "sleep", no_sleep)
    r = _Redis(delivered)
    await stream._handle_one(r, "t", "g", handler, ("1-1", {"data": '{"raw_item_id": "x"}'}))
    return r, counted


@pytest.mark.parametrize("delivered", [1, 2])
async def test_a_timed_out_statement_is_left_pending_on_its_first_deliveries(delivered, fresh_engine, monkeypatch):
    exc, _ = await _cancelled_statement(monkeypatch)
    r, _ = await _handle(exc, delivered, monkeypatch)
    assert r.acked == [] and r.dead == []


async def test_a_statement_that_times_out_on_every_delivery_is_dead_lettered(fresh_engine, monkeypatch):
    # Arrange
    exc, _ = await _cancelled_statement(monkeypatch)

    # Act
    r, counted = await _handle(exc, stream.STATEMENT_TIMEOUT_DELIVERIES, monkeypatch)

    # Assert
    assert r.acked == ["1-1"] and r.dead == ["t.dead"]
    assert "dead.t.statement_timeout" in counted


async def test_a_connection_error_never_dead_letters(monkeypatch):
    r, _ = await _handle(ConnectionError("db away"), 50, monkeypatch)
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
