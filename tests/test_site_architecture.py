"""The P0 site-architecture fixes that live in the API (marketing audit 02).

The news sitemap had lived on the feed's newest hundred rows and listed about
10 records when hundreds were eligible; it now has its own query, bounded by
the FIRST report's publication (Google News reads 48 hours) and the records
sitemap's indexable rule. The record carries its subject path, so the story
page can link the subject pages that nothing else linked.
"""

import datetime as dt
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


async def _record(s, source_id: uuid.UUID, slugs: list[str], published: list[dt.datetime], subject: str | None = None) -> uuid.UUID:
    """A record rebuilt now, from reports published at `published`."""
    eid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO events (id, title, summary, sector, subject_path, regions, projection, last_updated_at) "
             "VALUES (:i, 'A & B', 's', 'politics', :sp, ARRAY['IN'], CAST(:p AS jsonb), now())"),
        {"i": str(eid), "sp": subject, "p": f'{{"source_slugs": {str(slugs).replace(chr(39), chr(34))}}}'},
    )
    for when in published:
        rid, aid = uuid.uuid4(), uuid.uuid4()
        await s.execute(
            text("INSERT INTO raw_items (id, source_id, external_id, title, raw, relevance, published_at) "
                 "VALUES (:i, :s, :e, 'a headline', '{}'::jsonb, 'relevant', :w)"),
            {"i": str(rid), "s": str(source_id), "e": f"ext-{aid}", "w": when},
        )
        await s.execute(
            text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                 "VALUES (:i, :r, 'body', 'rss', 1)"),
            {"i": str(aid), "r": str(rid)},
        )
        await s.execute(
            text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                 "VALUES (:i, :e, :a, 'embedding', false)"),
            {"i": str(uuid.uuid4()), "e": str(eid), "a": str(aid)},
        )
    return eid


async def _source(s, slug: str, publisher: str) -> uuid.UUID:
    sid = uuid.uuid4()
    await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher) VALUES (:i, :s, :s, 'rss', :p)"),
                    {"i": str(sid), "s": slug, "p": publisher})
    return sid


async def _teardown(tag: str, events: list[uuid.UUID]) -> None:
    ids = [str(e) for e in events]
    async with session_scope() as s:
        arts = (await s.execute(text("SELECT article_id FROM event_memberships WHERE event_id = ANY(CAST(:e AS uuid[]))"), {"e": ids})).scalars().all()
        await s.execute(text("DELETE FROM event_memberships WHERE event_id = ANY(CAST(:e AS uuid[]))"), {"e": ids})
        await s.execute(text("DELETE FROM articles WHERE id = ANY(:a)"), {"a": list(arts)})
        await s.execute(text("DELETE FROM raw_items WHERE source_id IN (SELECT id FROM sources WHERE slug LIKE :p)"), {"p": f"zz_{tag}_%"})
        await s.execute(text("DELETE FROM sources WHERE slug LIKE :p"), {"p": f"zz_{tag}_%"})
        await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": ids})
    outlets.reset_cache()


async def test_the_news_sitemap_lists_what_was_first_reported_in_48_hours_and_asks_to_be_indexed():
    if not await _db_reachable():
        pytest.skip("no database")
    now = dt.datetime.now(dt.UTC)

    def ago(hours: float) -> dt.datetime:
        return now - dt.timedelta(hours=hours)

    tag = uuid.uuid4().hex[:6]
    two = [f"zz_{tag}_a", f"zz_{tag}_b"]  # unregistered: each counts as its own outlet
    house = [f"zz_{tag}_x", f"zz_{tag}_y"]  # two feeds of one publisher: one outlet
    async with session_scope() as s:
        sid = await _source(s, f"zz_{tag}_src", f"zz_{tag}_src")
        for slug in house:
            await _source(s, slug, f"zz_{tag}_house")
        fresh = await _record(s, sid, two, [ago(3), ago(10)])
        # Updated an hour ago, but FIRST reported 60 hours ago: not news any more.
        old = await _record(s, sid, two, [ago(60), ago(1)])
        single = await _record(s, sid, two[:1], [ago(2)])
        one_house = await _record(s, sid, house, [ago(2)])
        undated = await _record(s, sid, two, [None])
    outlets.reset_cache()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            res = await c.get("/api/v1/sitemap/news")
    finally:
        await _teardown(tag, [fresh, old, single, one_house, undated])
    assert res.status_code == 200
    listed = {r["id"]: r for r in res.json()["records"]}
    assert str(fresh) in listed
    assert listed[str(fresh)]["title"] == "A & B"
    # The first report's time, never the latest's or the rebuild's.
    assert dt.datetime.fromisoformat(listed[str(fresh)]["published_at"]) == ago(10)
    assert str(old) not in listed, "the 48 hours count from the first report"
    assert str(single) not in listed, "one outlet asks not to be indexed"
    assert str(one_house) not in listed, "two feeds of one publisher are one outlet (record_indexable, not the SQL's cut)"
    assert str(undated) not in listed, "no report carries a date: none is invented"


async def test_a_record_carries_its_subject_path():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    async with session_scope() as s:
        sid = await _source(s, f"zz_{tag}_src", f"zz_{tag}_src")
        eid = await _record(s, sid, [f"zz_{tag}_a"], [], subject="politics.elections")
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            body = (await c.get(f"/api/v1/events/{eid}")).json()
    finally:
        await _teardown(tag, [eid])
    assert body["subject_path"] == "politics.elections"
