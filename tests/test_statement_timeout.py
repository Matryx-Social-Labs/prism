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
async def test_a_timeout_that_is_not_a_plain_duration_is_refused(value, monkeypatch):
    monkeypatch.setattr(db, "_engine", None)
    monkeypatch.setattr(db, "_default_statement_timeout", None)
    with pytest.raises(ValueError):
        db.set_default_statement_timeout(value)
    with pytest.raises(ValueError):
        async with db.session_scope(statement_timeout=value):
            pass


async def test_a_scope_override_cancels_a_long_statement_and_is_counted(fresh_engine, monkeypatch):
    # Act
    exc, counted = await _cancelled_statement(monkeypatch)

    # Assert
    assert stream.sqlstate_in_chain(exc, {"57014"})
    assert counted == ["db.statement_timeout"]


async def test_a_cancelled_statement_is_transient_not_dead_lettered(fresh_engine, monkeypatch):
    exc, _ = await _cancelled_statement(monkeypatch)
    assert stream._is_transient(exc)


async def test_a_lock_that_cannot_be_had_in_time_is_transient(fresh_engine):
    # Arrange: one connection holds an advisory lock for its transaction
    key = 727_002
    async with db.get_engine().connect() as holder:
        await holder.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})

        # Act: another waits for it under a short lock_timeout
        with pytest.raises(DBAPIError) as caught:
            async with db.session_scope() as s:
                await s.execute(text("SET LOCAL lock_timeout = '50ms'"))
                await s.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": key})
        await holder.rollback()

    # Assert
    assert stream.sqlstate_in_chain(caught.value, {"55P03"})
    assert stream._is_transient(caught.value)


async def test_an_ordinary_failure_is_still_permanent(fresh_engine):
    with pytest.raises(IntegrityError) as caught:
        async with db.session_scope() as s:
            await s.execute(text("CREATE TEMP TABLE t_once (id int PRIMARY KEY)"))
            await s.execute(text("INSERT INTO t_once VALUES (1), (1)"))
    assert not stream._is_transient(caught.value)
    assert not stream._is_transient(ValueError("bad payload"))


@pytest.mark.parametrize(("env", "expected"), [(None, "5s"), ("3s", "3s")])
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
