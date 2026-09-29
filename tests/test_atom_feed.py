"""The Atom feed's records (/api/v1/sitemap/atom → web /feed.xml).

A feed reader is one more crawler, so the feed lists exactly what the records
sitemap lists (common/outlets.record_indexable: two outlets or more, two feeds
of one masthead counting once), newest report first, dated by the newest
report and never later than Prism's own rebuild of the record.
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


async def _seed(slugs: list[str], rebuilt: dt.datetime, published: dt.datetime | None, summary: str = "s") -> uuid.UUID:
    eid = uuid.uuid4()
    projection = {"source_slugs": slugs, **({"latest_published_at": published.isoformat()} if published else {})}
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector, regions, projection, last_updated_at) "
                 "VALUES (:i, :t, :s, 'politics', ARRAY['IN'], CAST(:p AS jsonb), :w)"),
            {"i": str(eid), "t": f"Record {eid.hex[:6]} & <co>", "s": summary, "p": json.dumps(projection), "w": rebuilt},
        )
    return eid


async def test_the_feed_lists_what_the_sitemap_lists_newest_report_first():
    if not await _db_reachable():
        pytest.skip("no database")
    now = dt.datetime.now(dt.UTC)
    tag = uuid.uuid4().hex[:6]
    feeds = [f"zz_{tag}_pub_x", f"zz_{tag}_pub_y"]
    async with session_scope() as s:
        for slug in feeds:
            await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher) VALUES (:i, :s, :s, 'rss', :p)"),
                            {"i": str(uuid.uuid4()), "s": slug, "p": f"zz_{tag}_one_house"})
    outlets.reset_cache()
    pair = [f"zz_{tag}_a", f"zz_{tag}_b"]
    two = await _seed(pair, now, now - dt.timedelta(minutes=5))
    one = await _seed([f"zz_{tag}_a"], now, now - dt.timedelta(minutes=4))
    house = await _seed(feeds, now, now - dt.timedelta(minutes=3))
    undated = await _seed(pair, now, None)
    # A report stamped a day ahead, rebuilt an hour ago: dated by the rebuild, not the stamp.
    ahead = await _seed(pair, now - dt.timedelta(hours=1), now + dt.timedelta(days=1), summary="")
    ids = (two, one, house, undated, ahead)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            records = (await c.get("/api/v1/sitemap/atom")).json()["records"]
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": [str(i) for i in ids]})
            await s.execute(text("DELETE FROM sources WHERE slug = ANY(:s)"), {"s": feeds})
        outlets.reset_cache()
    ours = [r for r in records if r["id"] in {str(i) for i in ids}]
    assert [r["id"] for r in ours] == [str(two), str(ahead)], "two outlets only, dated reports only, newest report first"
    assert dt.datetime.fromisoformat(ours[0]["updated"]) == now - dt.timedelta(minutes=5)
    assert dt.datetime.fromisoformat(ours[1]["updated"]) == now - dt.timedelta(hours=1), "never later than the rebuild"
    assert ours[0]["summary"] == "s" and ours[1]["summary"] is None
    assert len(records) <= 50


def test_the_publishers_page_states_the_quote_context_the_api_serves():
    """/for-publishers tells an outlet how much of its article a record shows
    beside a quote; that number is api/routes/events.CONTEXT_CHARS."""
    from pathlib import Path

    from api.routes.events import CONTEXT_CHARS

    page = (Path(__file__).parents[1] / "web/src/app/for-publishers/page.tsx").read_text()
    assert f"at most {CONTEXT_CHARS} characters of the article either side" in page
