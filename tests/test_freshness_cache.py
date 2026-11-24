"""/healthz reads freshness from a one-minute cache.

The freshness SQL scans whole tables and every probe ran it; probes must not be
able to pile queries onto a database that is already struggling.
"""

import asyncio
from datetime import datetime

import pytest

from common import freshness


@pytest.fixture
def calls(monkeypatch) -> list[int]:
    """Stub the query; record each window it ran for."""
    ran: list[int] = []

    async def query(db, *, window_hours):
        ran.append(window_hours)
        await asyncio.sleep(0.01)  # long enough for concurrent callers to overlap
        return {"ok": True, "window_hours": window_hours}

    monkeypatch.setattr(freshness, "pipeline_freshness", query)
    return ran


async def test_a_second_call_within_the_ttl_runs_no_query(calls):
    first = await freshness.cached(None)
    second = await freshness.cached(None)
    assert calls == [freshness.WINDOW_HOURS]
    assert second == first


async def test_a_call_after_the_ttl_runs_the_query_again(calls, monkeypatch):
    await freshness.cached(None)
    monkeypatch.setattr(freshness, "CACHE_TTL_S", 0)  # every entry is now past its TTL
    await freshness.cached(None)
    assert len(calls) == 2


async def test_each_window_is_cached_on_its_own_and_clamped(calls):
    await freshness.cached(None, window_hours=6)
    await freshness.cached(None, window_hours=6)
    await freshness.cached(None, window_hours=12)
    await freshness.cached(None, window_hours=10_000)
    await freshness.cached(None, window_hours=freshness.MAX_WINDOW_HOURS)
    assert calls == [6, 12, freshness.MAX_WINDOW_HOURS]


async def test_an_unavailable_result_is_cached_too(monkeypatch):
    ran: list[int] = []

    async def failing(db, *, window_hours):
        ran.append(window_hours)
        return {"ok": None, "window_hours": window_hours, "error": "unavailable"}

    monkeypatch.setattr(freshness, "pipeline_freshness", failing)
    await freshness.cached(None)
    assert (await freshness.cached(None))["error"] == "unavailable"
    assert len(ran) == 1


async def test_concurrent_probes_at_expiry_run_one_query(calls):
    results = await asyncio.gather(*(freshness.cached(None) for _ in range(5)))
    assert calls == [freshness.WINDOW_HOURS]
    assert all(r == results[0] for r in results)


async def test_a_cached_answer_says_when_its_query_ran(calls):
    first = await freshness.cached(None)
    await asyncio.sleep(0.01)
    second = await freshness.cached(None)
    assert datetime.fromisoformat(first["as_of"]).tzinfo is not None
    assert second["as_of"] == first["as_of"]


async def test_healthz_twice_runs_the_freshness_query_once(calls, monkeypatch):
    # Arrange: everything else /healthz reads is stubbed; only freshness is counted
    from api.routes import meta

    async def nothing(*_args, **_kwargs):
        return {}

    class _Db:
        async def execute(self, _statement):
            return None

    monkeypatch.setattr(meta, "backlog", nothing)
    monkeypatch.setattr(meta, "check_corpus_model", nothing)

    # Act
    for _ in range(2):
        await meta.healthz(db=_Db(), freshness_window_hours=freshness.WINDOW_HOURS)

    # Assert
    assert calls == [freshness.WINDOW_HOURS]
