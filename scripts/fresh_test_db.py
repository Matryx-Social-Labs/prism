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


async def main() -> None:
    url = urlparse(os.environ.get("DATABASE_URL", "").replace("+asyncpg", ""))
    name = url.path.lstrip("/")
    if not re.fullmatch(r"\w+_test", name) or url.query:
        sys.exit(f"fresh_test_db: refusing to drop {name!r}: not a plain _test database")
    conn = await asyncpg.connect(url._replace(path="/postgres").geturl(), timeout=10)
    try:
        await conn.execute(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)')
        await conn.execute(f'CREATE DATABASE "{name}"')
    finally:
        await conn.close()
    print(f"  fresh test database: {name}")


asyncio.run(main())
