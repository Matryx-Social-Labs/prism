"""Run the DB-backed tests only on a database whose name ends in _test.

Several tests here are destructive by nature: they INSERT events, publish
partition runs, and run
`UPDATE partition_runs SET status='superseded' WHERE status='current'`, which
detaches every live storyline.

Each workspace has its own test database, `prism_<workspace>_test`, created by
`scripts/workspace_setup.sh` and named in `.env` as `TEST_DATABASE_URL`. This
module points `DATABASE_URL` at it before anything reads settings, so the suite
never touches the workspace's dev database. CI names its database `prism_test`.

The guard then refuses any database whose name does not end in `_test`. A local
host used to be enough, and that is how the shared dev database filled with
fixture rows. `_db_reachable()` in the test modules only asks whether *a*
database answers, so a production URL passes that check more easily than a
stopped local one, and this repo does reach production over the Railway public
proxy for admin queries.

Fail loudly rather than skip: a skip would look like a pass in CI.
"""

import os
from urllib.parse import parse_qs, urlparse

import pytest
from dotenv import dotenv_values

_test_database_url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(".env").get("TEST_DATABASE_URL")
if _test_database_url:
    os.environ["DATABASE_URL"] = _test_database_url


def database_refusal(url: str) -> str | None:
    """Why the suite must not run against `url`, or None when it may."""
    parsed = urlparse(url)
    name = parsed.path.lstrip("/")
    # `?database=` overrides the path in SQLAlchemy's asyncpg dialect.
    if name.endswith("_test") and "database" not in parse_qs(parsed.query):
        return None
    return (
        f"Refusing to run tests against database {name!r} on {parsed.hostname!r}: "
        "its name does not end in _test.\n"
        "These tests insert events and supersede partition runs — they would corrupt it.\n"
        "Run `bash scripts/workspace_setup.sh` to create this workspace's test database, "
        "or set TEST_DATABASE_URL to a database whose name ends in _test."
    )


@pytest.fixture(scope="session", autouse=True)
def refuse_non_test_database() -> None:
    from common.config import get_settings

    refusal = database_refusal(get_settings().database_url)
    if refusal:
        pytest.exit(refusal, returncode=2)


@pytest.fixture(autouse=True)
async def _dispose_engine_between_tests():
    """Drop pooled connections after every test.

    pyproject sets `asyncio_mode = "auto"`, so pytest-asyncio gives each test a
    FRESH event loop, while common/db.py holds a module-level engine with
    pool_size=20. A connection opened on one test's loop and handed to the next
    raises `RuntimeError: got Future attached to a different loop` from deep
    inside asyncpg, and `pool_pre_ping` cannot save it because the ping itself
    runs on the wrong loop.

    Whether that fires depends purely on which test happened to open a connection
    first, so the suite passed by luck of ordering and adding a new DB-backed test
    file was enough to break it. Worse, the test modules guard with
    `_db_reachable()`, so the crash surfaced as "no database" and the test SKIPPED
    — green, and testing nothing. That is the failure mode conftest's own
    docstring warns about two paragraphs up.

    Disposing between tests costs a reconnect per test and removes the ordering
    dependency entirely.
    """
    yield
    from common.db import get_engine

    engine = get_engine()
    if engine is not None:
        await engine.dispose()


@pytest.fixture(autouse=True)
def _fresh_freshness_cache():
    """/healthz caches freshness for a minute per process; every test starts
    without one (and with a lock not bound to an earlier test's loop)."""
    from common import freshness

    freshness.reset_cache()
    yield


# --- PRISM_REQUIRE_DB: make skip-as-pass impossible in CI ---------------------


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Turn a "no database" or "no redis" SKIP into a FAILURE when PRISM_REQUIRE_DB=1.

    20 test modules guard themselves with `_db_reachable()` and skip when
    Postgres is absent. That is right for a laptop with no docker running, and
    wrong everywhere it matters: on a machine without Postgres, ~88 assertions
    across those modules vanish and the suite still reports green. A green suite
    that ran a third of its tests is worse than a red one, because nobody looks.

    This repo has already been bitten by exactly that: an event-loop bug made
    real failures surface through `_db_reachable()` as "no database", so broken
    tests reported as skips (see `_dispose_engine_between_tests` above). The
    guard against a class of bug should not be able to hide that same class of
    bug.

    Opt-in rather than always-on, because a skip is the correct behaviour when a
    contributor genuinely has no database. CI and `make check` set the flag.
    """
    import os

    outcome = yield
    if not os.environ.get("PRISM_REQUIRE_DB"):
        return
    report = outcome.get_result()
    if not report.skipped:
        return
    # Redis too: CI and `make check` have it, and a client bound to an earlier
    # test's closed loop surfaces as exactly this skip (tests/test_pipeline_recovery.fresh_redis).
    missing = next((m for m in ("no database", "no redis") if m in str(report.longrepr)), None)
    if missing:
        report.outcome = "failed"
        report.longrepr = (
            f"{item.nodeid}: skipped for '{missing}' while PRISM_REQUIRE_DB=1.\n"
            "A test that needs a service it cannot reach is a FAILURE here, "
            "not a skip — otherwise the suite reports green having silently not run.\n"
            "Start them with:  docker compose up -d postgres redis"
        )
