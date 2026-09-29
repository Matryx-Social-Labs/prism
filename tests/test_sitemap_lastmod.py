"""The records sitemap's lastmod is the news's clock, not the rebuild's (audit 01 P2-11).

`events.last_updated_at` is set on every projection rebuild, so 303 URLs in
records-sitemap.xml shared the hour 2026-09-24T14. Google uses lastmod only
while it stays verifiably accurate, so it is now the newest report's
publication, and never later than the rebuild that took that report in.
"""

import datetime as dt
import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import outlets
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed(tag: str, rebuilt: dt.datetime, newest_report: dt.datetime | None) -> uuid.UUID:
    eid = uuid.uuid4()
    projection = {"source_slugs": [f"zz_{tag}_a", f"zz_{tag}_b"]}
    if newest_report:
        projection["latest_published_at"] = newest_report.isoformat()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector, regions, projection, last_updated_at) "
                 "VALUES (:i, 'A record', 's', 'politics', ARRAY['IN'], CAST(:p AS jsonb), :w)"),
            {"i": str(eid), "p": json.dumps(projection), "w": rebuilt},
        )
    return eid


async def test_lastmod_is_the_newest_report_never_the_rebuild_clock():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    rebuilt = dt.datetime.now(dt.UTC).replace(microsecond=0) - dt.timedelta(days=60)  # out of the feed's way
    reported = rebuilt - dt.timedelta(days=3)
    outlets.reset_cache()
    dated = await _seed(tag, rebuilt, reported)
    undated = await _seed(tag, rebuilt, None)
    # A publisher's clock ahead of ours (a wrong timezone): capped at the rebuild.
    ahead = await _seed(tag, rebuilt, rebuilt + dt.timedelta(hours=5))
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            rows = (await c.get("/api/v1/sitemap/records")).json()["records"]
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"),
                            {"e": [str(i) for i in (dated, undated, ahead)]})
    lastmod = {r["id"]: dt.datetime.fromisoformat(r["lastmod"]) for r in rows}
    assert lastmod[str(dated)] == reported
    assert lastmod[str(undated)] == rebuilt
    assert lastmod[str(ahead)] == rebuilt
