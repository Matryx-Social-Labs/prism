"""The coverage network behind /admin/coverage (admin charts, phase 6).

Seeded in March 2032, where nothing else in a developer's database lives, so
every count below is exact: outlets are linked by the stories both reported,
a story outside the period links nobody, and a story reported in two
languages is counted once per pair of languages, not once per pair of outlets.
"""

import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common import coverage, metrics
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")

TODAY = date(2032, 3, 31)
IST = timezone(timedelta(hours=5, minutes=30))


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def test_outlets_are_linked_by_the_stories_they_share(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    a, b, h = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    names = {a: f"A {tag}", b: f"B {tag}", h: f"H {tag}"}
    inside = datetime(2032, 3, 20, 12, tzinfo=IST)
    before = datetime(2032, 3, 3, 12, tzinfo=IST)  # the day before the 28 days (4–31 Mar)
    # (created, outlets): a+b twice, a+h, a alone, and b+h the day before the period.
    stories = [(inside, (a, b)), (inside, (a, b, a)), (inside, (a, h)), (inside, (a,)), (before, (b, h))]
    events = [uuid.uuid4() for _ in stories]
    try:
        async with session_scope() as s:
            for src, lang in ((a, "en"), (b, "en"), (h, "hi")):
                await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher, country, language) "
                                     "VALUES (:i, :s, :n, 'rss', :s, 'IN', :l)"),
                                {"i": src, "s": f"cov-{src.hex[:10]}", "n": names[src], "l": lang})
            for ev, (created, outlets) in zip(events, stories, strict=True):
                await s.execute(text("INSERT INTO events (id, title, summary, last_updated_at, created_at) "
                                     "VALUES (:e, 't', 's', now(), :c)"), {"e": ev, "c": created})
                # The second story has two reports from A: still one story for A.
                for src in outlets:
                    raw, art = uuid.uuid4(), uuid.uuid4()
                    await s.execute(text("INSERT INTO raw_items (id, source_id, external_id, url, title, published_at, language, raw, relevance) "
                                         "VALUES (:r, :s, :x, :u, 't', :p, 'en', '{}', 'relevant')"),
                                    {"r": raw, "s": src, "x": f"cov-{raw.hex}", "u": f"https://example.org/cov/{raw.hex}", "p": created})
                    await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                                         "VALUES (:a, :r, 'x', 'feed', 1)"), {"a": art, "r": raw})
                    await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                                         "VALUES (gen_random_uuid(), :e, :a, 'new_event', true)"), {"e": ev, "a": art})
        async with session_scope() as s:
            net = await coverage.network(s, metrics.window(28, TODAY))

        mine = {o["name"]: o for o in net["outlets"] if tag in o["name"]}
        by_id = {o["id"]: o["name"] for o in net["outlets"]}
        assert (mine[names[a]]["stories"], mine[names[a]]["shared"]) == (4, 3)
        assert (mine[names[b]]["stories"], mine[names[b]]["shared"]) == (2, 2)
        assert (mine[names[h]]["stories"], mine[names[h]]["shared"]) == (1, 1)
        assert mine[names[h]]["language"] == "hi"
        links = {frozenset((by_id[x["a"]], by_id[x["b"]])): x["shared"] for x in net["links"]}
        assert links == {frozenset((names[a], names[b])): 2, frozenset((names[a], names[h])): 1}
        # One story in both English and Hindi, however many outlets carried it.
        assert net["languages"] == [{"a": "en", "b": "hi", "stories": 1}]
        assert {r["language"]: r["stories"] for r in net["per_language"]} == {"en": 4, "hi": 1}
        # Capped at the outlets with the most stories, in SQL: no link reaches one left out.
        monkeypatch.setattr(coverage, "MAX_OUTLETS", 1)
        async with session_scope() as s:
            top = await coverage.network(s, metrics.window(28, TODAY))
        assert len(top["outlets"]) == 1 and top["links"] == []
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = ANY(:e)"), {"e": events})
            await s.execute(text("DELETE FROM articles WHERE raw_item_id IN (SELECT id FROM raw_items WHERE source_id = ANY(:s))"), {"s": [a, b, h]})
            await s.execute(text("DELETE FROM raw_items WHERE source_id = ANY(:s)"), {"s": [a, b, h]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"), {"e": events})
            await s.execute(text("DELETE FROM sources WHERE id = ANY(:s)"), {"s": [a, b, h]})


async def test_only_a_founder_reads_the_network():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        assert (await c.get("/api/v1/admin/coverage")).status_code == 401
