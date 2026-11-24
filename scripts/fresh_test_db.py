"""Drop and recreate the test database named by DATABASE_URL, empty.

The suite is written for CI's empty database: every run leaves ~165 events
behind, and by the fourth run on the same database tests that read one feed
page (tests/test_geo.py) no longer find the rows they seeded. `make check` runs
this first, so the gate sees what CI sees however long the workspace has lived.
"""

import asyncio
import os
import re
import sys
from urllib.parse import urlparse

import asyncpg

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


def refusal(url: str) -> str | None:
    """Why `url` must not be dropped, or None when it is a local, plainly named _test database."""
    parsed = urlparse(url)
    name = parsed.path.lstrip("/")
    if re.fullmatch(r"\w+_test", name) and not parsed.query and parsed.hostname in LOCAL_HOSTS:
        return None
    return f"fresh_test_db: refusing to drop {name!r} on {parsed.hostname!r}: not a local _test database"


async def main() -> None:
    dsn = os.environ.get("DATABASE_URL", "").replace("+asyncpg", "")
    if message := refusal(dsn):
        sys.exit(message)
    url = urlparse(dsn)
    name = url.path.lstrip("/")
    conn = await asyncpg.connect(url._replace(path="/postgres").geturl(), timeout=10)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{name}"')
    finally:
        await conn.close()
    print(f"  fresh test database: {name}")


if __name__ == "__main__":
    asyncio.run(main())
