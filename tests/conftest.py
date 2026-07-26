"""Refuse to run the DB-backed tests against anything but a local database.

There is no test database in this project — `DATABASE_URL` is whatever the
developer has configured, and several tests here are destructive by nature:
they INSERT events, publish partition runs, and run
`UPDATE partition_runs SET status='superseded' WHERE status='current'`, which
detaches every live storyline.

`_db_reachable()` in the test modules only asks whether *a* database answers, so
a production URL passes that check more easily than a stopped local one. This
repo does reach production over the Railway public proxy for admin queries, so a
`DATABASE_URL` left exported in a shell is a real path to running the suite
against live data.

Fail loudly rather than skip: a skip would look like a pass in CI.
"""

from urllib.parse import urlparse

import pytest

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "db", "postgres"}


@pytest.fixture(scope="session", autouse=True)
def refuse_non_local_database() -> None:
    from common.config import get_settings

    url = getattr(get_settings(), "database_url", "") or ""
    if not url:
        return  # nothing configured; the per-test _db_reachable guards handle it

    host = urlparse(url.replace("postgresql+asyncpg://", "postgresql://")).hostname
    name = (urlparse(url).path or "").lstrip("/")
    if host in _LOCAL_HOSTS or name.endswith("_test"):
        return

    pytest.exit(
        f"Refusing to run tests against a non-local database (host={host!r}, db={name!r}).\n"
        "These tests insert events and supersede partition runs — they would corrupt it.\n"
        "Point DATABASE_URL at localhost, or name the database with a _test suffix.",
        returncode=2,
    )
