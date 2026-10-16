from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from common.config import get_settings

# Longest any one statement may run inside an API request.
API_STATEMENT_TIMEOUT = "30s"

_engine = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


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
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(get_engine(), expire_on_commit=False)
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Transactional scope: commits on success, rolls back on error."""
    async with get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
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
