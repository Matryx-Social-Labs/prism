"""Which records ask search engines to index them (common/outlets.record_indexable).

Search Console, 2026-09-21: of the 19 records Google crawled and chose not to
index, 13 were built from ONE outlet. A one-outlet record is a rewrite of that
outlet's article, and Google keeps the original. Prism's own value is the same
story across outlets, so a record asks to be indexed from its second outlet on
(86% of 90 days' records had a single source). It stays readable and linked;
the page's robots, the feed row, the records sitemap and IndexNow all read the
one rule, so they cannot disagree.
"""

import datetime as dt
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from api.routes.serialization import build_feed_item
from common import indexnow, outlets
from common.config import get_settings
from common.db import session_scope
from common.lenses import get_lens
from common.outlets import Outlet, record_indexable

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _outlet(slug: str, publisher: str) -> Outlet:
    return Outlet(slug=slug, publisher=publisher, name=slug, code=slug[:3].upper(), origin="national", language="en", country="IN")


REGISTRY = {
    "hindu_national": _outlet("hindu_national", "thehindu"),
    "hindu_karnataka": _outlet("hindu_karnataka", "thehindu"),
    "express": _outlet("express", "indianexpress"),
}


def test_one_outlet_is_not_enough():
    assert record_indexable(["hindu_national"], REGISTRY) is False
    assert record_indexable([], REGISTRY) is False


def test_two_feeds_of_one_publisher_are_one_outlet():
    """The page prints outlets by publisher (lib/coverage.publishers); so does the rule."""
    assert record_indexable(["hindu_national", "hindu_karnataka"], REGISTRY) is False


def test_a_second_publisher_makes_it_a_record_worth_indexing():
    assert record_indexable(["hindu_national", "express"], REGISTRY) is True


def test_unregistered_sources_count_as_themselves():
    """As the page does when none of a record's sources is registered."""
    assert record_indexable(["zz_a", "zz_b"], {}) is True
    assert record_indexable(["zz_a"], None) is False


def test_a_feed_row_carries_the_rule():
    row = {"id": uuid.uuid4(), "title": "t", "summary": None, "sector": "politics", "subsector": None, "regions": [],
           "image_url": None, "occurred_at": None, "last_updated_at": dt.datetime.now(dt.UTC),
           "projection": {"source_slugs": ["hindu_national"]}}
    assert build_feed_item(row, get_lens(None), None, registry=REGISTRY).indexable is False
    row["projection"] = {"source_slugs": ["hindu_national", "express"]}
    assert build_feed_item(row, get_lens(None), None, registry=REGISTRY).indexable is True


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed(slugs: list[str], when: dt.datetime) -> uuid.UUID:
    eid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector, regions, projection, last_updated_at) "
                 "VALUES (:i, 'A record', 's', 'politics', ARRAY['IN'], CAST(:p AS jsonb), :w)"),
            {"i": str(eid), "p": f'{{"source_slugs": {str(slugs).replace(chr(39), chr(34))}}}', "w": when},
        )
    return eid


async def _drop(*ids: uuid.UUID) -> None:
    async with session_scope() as s:
        await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": [str(i) for i in ids]})


async def test_the_record_page_and_the_sitemap_agree():
    """Including the case the SQL alone would get wrong: two feeds of one publisher."""
    if not await _db_reachable():
        pytest.skip("no database")
    long_ago = dt.datetime.now(dt.UTC) - dt.timedelta(days=60)  # out of the feed's way (test_geo)
    tag = uuid.uuid4().hex[:6]
    feeds = [f"zz_{tag}_pub_x", f"zz_{tag}_pub_y"]
    async with session_scope() as s:
        for slug in feeds:
            await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher) VALUES (:i, :s, :s, 'rss', :p)"),
                            {"i": str(uuid.uuid4()), "s": slug, "p": f"zz_{tag}_one_house"})
    outlets.reset_cache()
    one = await _seed([f"zz_{tag}_a"], long_ago)
    two = await _seed([f"zz_{tag}_a", f"zz_{tag}_b"], long_ago)
    house = await _seed(feeds, long_ago)
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            flags = {i: (await c.get(f"/api/v1/events/{i}")).json()["indexable"] for i in (one, two, house)}
            listed = {r["id"] for r in (await c.get("/api/v1/sitemap/records")).json()["records"]}
    finally:
        await _drop(one, two, house)
        async with session_scope() as s:
            await s.execute(text("DELETE FROM sources WHERE slug = ANY(:s)"), {"s": feeds})
        outlets.reset_cache()
    assert flags == {one: False, two: True, house: False}
    assert {str(one), str(two), str(house)} & listed == {str(two)}, "the sitemap must offer exactly what the page asks to have indexed"


async def test_indexnow_offers_only_what_asks_to_be_indexed():
    if not await _db_reachable():
        pytest.skip("no database")
    now = dt.datetime.now(dt.UTC)
    tag = uuid.uuid4().hex[:6]
    one, two = await _seed([f"zz_{tag}_a"], now), await _seed([f"zz_{tag}_a", f"zz_{tag}_b"], now)
    try:
        async with session_scope() as s:
            urls = await indexnow.changed_urls(s)
    finally:
        await _drop(one, two)
    web = get_settings().prism_web_url.rstrip("/")
    assert f"{web}/story/{two}" in urls and f"{web}/story/{one}" not in urls
    # Every story is provisional until the boundary is promoted, and a
    # provisional story asks not to be indexed.
    assert not [u for u in urls if "/trending/" in u]
