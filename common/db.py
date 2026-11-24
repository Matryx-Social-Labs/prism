import os
import re
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from common.config import get_settings
from common.logging import get_logger

logger = get_logger(__name__)

# Longest any one statement may run inside an API request.
API_STATEMENT_TIMEOUT = "30s"
# The worker's default (PRISM_WORKER_STATEMENT_TIMEOUT overrides; 0 = off). No
# worker statement has a measured duration near it; it exists so that none can
# run unbounded, as the API's could until 2026-10-16.
WORKER_STATEMENT_TIMEOUT = "120s"
# A migration that cannot get its lock in this long fails the deploy instead of
# queueing every reader behind its DDL (PRISM_MIGRATION_LOCK_TIMEOUT overrides).
MIGRATION_LOCK_TIMEOUT = "5s"
# Startup settings are checked here so a typo fails at boot with a clear message.
_DURATION = re.compile(r"\d+(ms|s|min|h)?")
QUERY_CANCELED = "57014"  # SQLSTATE: statement_timeout (or a cancel) fired

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None
# None until the worker sets it at startup; the API and tools/ never do.
_default_statement_timeout: str | None = None


def sqlstate_in_chain(exc: BaseException | None, codes: set[str]) -> bool:
    """Whether a Postgres error with one of these SQLSTATEs is anywhere in the
    chain. asyncpg errors and SQLAlchemy's asyncpg adapter both carry `.sqlstate`;
    SQLAlchemy raises its DBAPIError from the adapter, so `__cause__` reaches it."""
    seen: set[int] = set()
    while exc is not None and id(exc) not in seen:
        seen.add(id(exc))
        if getattr(exc, "sqlstate", None) in codes:
            return True
        exc = exc.__cause__ or exc.__context__
    return False


def _duration(value: str) -> str:
    if not isinstance(value, str) or not _DURATION.fullmatch(value):
        raise ValueError(f"not a Postgres duration: {value!r}")
    return value


def set_default_statement_timeout(value: str | None) -> None:
    """The statement_timeout every connection of this process starts with."""
    global _default_statement_timeout
    if _engine is not None:
        raise RuntimeError("set the default statement timeout before the engine exists")
    _default_statement_timeout = None if value is None else _duration(value)


def server_settings() -> dict[str, str]:
    """asyncpg startup settings carrying the process default, for any connection
    this process opens (the pool, and correlation/variants' own)."""
    if _default_statement_timeout is None:
        return {}
    return {"statement_timeout": _default_statement_timeout}


def migration_connect_args() -> dict:
    """connect_args for alembic's engine (db/env.py)."""
    timeout = os.environ.get("PRISM_MIGRATION_LOCK_TIMEOUT") or MIGRATION_LOCK_TIMEOUT
    return {"server_settings": {"lock_timeout": _duration(timeout)}}


def get_engine():
    global _engine
    if _engine is None:
        # Pool sized for the worker's concurrent consumers (enrichment runs many
        # I/O-bound LLM extracts in parallel) plus the API's request handlers.
        _engine = create_async_engine(
            get_settings().database_url,
            pool_pre_ping=True,
            pool_size=20,
            max_overflow=20,
            # A startup setting, so every pooled connection carries it with no
            # per-transaction round trip; SET LOCAL still overrides it.
            connect_args={"server_settings": server_settings()},
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def session_scope(statement_timeout: str | None = None) -> AsyncIterator[AsyncSession]:
    """Transactional scope: commits on success, rolls back on error.

    `statement_timeout` overrides the process default for this transaction only
    (a caller that commits mid-scope loses it with the transaction)."""
    async with get_session_factory()() as session:
        try:
            if statement_timeout is not None:
                # Bound, and Postgres validates it: a bad value fails here.
                await session.execute(
                    text("SELECT set_config('statement_timeout', :v, true)"), {"v": statement_timeout}
                )
            yield session
            await session.commit()
        except Exception as exc:
            await session.rollback()
            if sqlstate_in_chain(exc, {QUERY_CANCELED}):
                from common import timings  # here: timings -> stream -> db at import

                logger.warning("statement_timeout_hit", error=str(exc)[:200])
                await timings.count("db.statement_timeout")
            raise


async def get_db() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency: commit on success so write endpoints (auth, later the
    paywall gate + watchlist) actually persist. Reads commit an empty tx (no-op).
    Without this, INSERT/UPDATE in a route silently roll back when the request ends.

    Every request gets a statement timeout. Without one, a slow query outlives the
    client that asked for it, and each new visit adds another copy: on 2026-10-16
    fifteen copies of one ran for up to 1h40m and their parallel workers filled
    /dev/shm, so every other query failed. The worker does not use this dependency.
    """
    async with get_session_factory()() as session:
        try:
            await session.execute(text(f"SET LOCAL statement_timeout = '{API_STATEMENT_TIMEOUT}'"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
