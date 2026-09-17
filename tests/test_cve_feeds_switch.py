"""CVE collection must be off until the Cyber tier, and off by DEFAULT.

The CVE feeds were the cyber beachhead and they dominate by volume: 19,276 of
27,194 articles and 77% of all events, none of which ever reached the general
feed. Their corpus was deleted on 2026-09-05; a collector that quietly kept
running would rebuild all of it inside a day.
"""

import pytest

from common.config import get_settings
from ingestion import runner

pytestmark = pytest.mark.asyncio


@pytest.fixture(autouse=True)
def _clear():
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


async def _run(monkeypatch) -> list[str]:
    called: list[str] = []

    async def fake(name):
        called.append(name)
        return 0

    monkeypatch.setattr(runner.rss, "collect", lambda: fake("rss"))
    monkeypatch.setattr(runner.nvd, "collect", lambda: fake("nvd"))
    monkeypatch.setattr(runner.cisa_kev, "collect", lambda: fake("cisa_kev"))
    monkeypatch.setattr(runner, "seed_sources", lambda: fake("seed"))

    async def no_requeue(limit=500):
        return 0

    monkeypatch.setattr(runner, "requeue_stalled", no_requeue)

    async def no_balance():
        return None

    monkeypatch.setattr(runner.budget, "current", no_balance)
    await runner.run_all()
    return called


async def test_cve_collectors_do_not_run_by_default(monkeypatch):
    monkeypatch.setenv("PRISM_INGESTION_ENABLED", "true")
    called = await _run(monkeypatch)
    assert "rss" in called
    assert "nvd" not in called and "cisa_kev" not in called


async def test_they_come_back_when_the_switch_is_on(monkeypatch):
    """Off is a decision, not a deletion. The Cyber tier turns them back on and
    the corpus rebuilds for free — public feeds, deterministic enrichment."""
    monkeypatch.setenv("PRISM_INGESTION_ENABLED", "true")
    monkeypatch.setenv("PRISM_CVE_FEEDS_ENABLED", "true")
    called = await _run(monkeypatch)
    assert {"rss", "nvd", "cisa_kev"} <= set(called)


async def test_the_master_switch_still_beats_everything(monkeypatch):
    monkeypatch.setenv("PRISM_INGESTION_ENABLED", "false")
    monkeypatch.setenv("PRISM_CVE_FEEDS_ENABLED", "true")
    assert await _run(monkeypatch) == []


async def test_the_article_cap_stops_collection_before_it_starts(monkeypatch):
    """A cap enforced AFTER collection is a report, not a brake.

    "Bounded article cap" and "watched" are not cost controls — the outside voice
    was right about that. This is the one quantity that cannot drift, and the
    check runs before any collector so hitting the ceiling costs nothing further.
    """
    monkeypatch.setenv("PRISM_INGESTION_ENABLED", "true")
    monkeypatch.setenv("PRISM_INGEST_MAX_ARTICLES", "100")
    get_settings.cache_clear()

    class _S:
        async def execute(self, *a, **kw):
            class R:
                def scalar_one(self_inner):
                    return 100  # already at the ceiling
            return R()

    class _Scope:
        async def __aenter__(self):
            return _S()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(runner, "session_scope", lambda: _Scope())
    called = await _run(monkeypatch)
    assert called == [], f"collectors ran past the cap: {called}"


async def test_below_the_cap_collection_proceeds(monkeypatch):
    monkeypatch.setenv("PRISM_INGESTION_ENABLED", "true")
    monkeypatch.setenv("PRISM_INGEST_MAX_ARTICLES", "100")
    get_settings.cache_clear()

    class _S:
        async def execute(self, *a, **kw):
            class R:
                def scalar_one(self_inner):
                    return 7
            return R()

    class _Scope:
        async def __aenter__(self):
            return _S()

        async def __aexit__(self, *a):
            return False

    monkeypatch.setattr(runner, "session_scope", lambda: _Scope())
    assert "rss" in await _run(monkeypatch)
