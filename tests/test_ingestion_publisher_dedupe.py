"""One article, one publisher, one trip through the pipeline.

The Hindu's six state pages and TOI's city pages carry one article under one
URL. Each copy used to be a new raw item under its own source — gated,
extracted and listed as its own report: 432 of 6,717 articles in the week to
2026-09-20 were such copies. The second observation is kept (relevance =
'duplicate') for provenance and never published; if it came through a state
page, the state goes onto the article's event.
"""

import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import text

import ingestion.base as base
from common.db import session_scope
from common.schemas import RawItemEnvelope

pytestmark = pytest.mark.asyncio(loop_scope="session")

URL = "https://www.thehindu.com/news/national/karnataka/test-dedupe-article/article99.ece"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _seed_and_cleanup():
    async with session_scope() as s:
        for slug, name in (("thehindu", "The Hindu"), ("thehindu_karnataka", "The Hindu — Karnataka")):
            await s.execute(
                text(
                    "INSERT INTO sources (id, slug, name, source_type, publisher, country, language) "
                    "VALUES (gen_random_uuid(), :slug, :name, 'rss', 'thehindu', 'IN', 'en') "
                    "ON CONFLICT (slug) DO NOTHING"
                ),
                {"slug": slug, "name": name},
            )
    yield
    async with session_scope() as s:
        await s.execute(text("DELETE FROM event_memberships WHERE article_id IN (SELECT id FROM articles WHERE raw_item_id IN (SELECT id FROM raw_items WHERE url_canonical LIKE '%test-dedupe-article%'))"))
        await s.execute(text("DELETE FROM articles WHERE raw_item_id IN (SELECT id FROM raw_items WHERE url_canonical LIKE '%test-dedupe-article%')"))
        await s.execute(text("DELETE FROM raw_items WHERE url_canonical LIKE '%test-dedupe-article%'"))
        await s.execute(text("DELETE FROM events WHERE title = 'dedupe-event'"))


def env(slug: str, ext: str) -> RawItemEnvelope:
    return RawItemEnvelope(source_slug=slug, source_type="rss", external_id=ext, url=URL, title="Test dedupe article", body="Body text " * 20, published_at=datetime.now(UTC), language="en", raw={})


async def _db() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


async def test_the_same_url_through_a_second_feed_of_the_publisher_is_not_re_ingested(monkeypatch):
    if not await _db():
        pytest.skip("no local database")
    published: list = []

    async def fake_publish(_topic, msg):
        published.append(msg)

    monkeypatch.setattr(base.stream, "publish", fake_publish)

    first = await base.persist_envelopes([env("thehindu", "a-1")])
    second = await base.persist_envelopes([env("thehindu_karnataka", "b-1")])
    assert (first, second) == (1, 0), "the second feed's copy must not count as new"
    assert len(published) == 1, "only the first copy goes down the pipeline"
    async with session_scope() as s:
        rows = (await s.execute(text("SELECT relevance FROM raw_items WHERE url_canonical LIKE '%test-dedupe-article%' ORDER BY created_at"))).scalars().all()
    assert rows == ["pending", "duplicate"], "the observation is kept, marked, never queued"


async def test_a_state_pages_copy_places_the_existing_event(monkeypatch):
    if not await _db():
        pytest.skip("no local database")

    async def fake_publish(_topic, _msg):
        return None

    monkeypatch.setattr(base.stream, "publish", fake_publish)
    await base.persist_envelopes([env("thehindu", "a-2")])
    # The first copy became an article on an India-wide event.
    async with session_scope() as s:
        raw_id = (await s.execute(text("SELECT id FROM raw_items WHERE url_canonical LIKE '%test-dedupe-article%' AND relevance = 'pending'"))).scalar_one()
        art_id, ev_id = uuid.uuid4(), uuid.uuid4()
        await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) VALUES (:a, :r, 'x', 'feed', 1)"), {"a": art_id, "r": raw_id})
        await s.execute(text("INSERT INTO events (id, title, summary, regions, last_updated_at) VALUES (:e, 'dedupe-event', 's', ARRAY['IN'], now())"), {"e": ev_id})
        await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) VALUES (gen_random_uuid(), :e, :a, 'new_event', true)"), {"e": ev_id, "a": art_id})
    await base.persist_envelopes([env("thehindu_karnataka", "b-2")])
    async with session_scope() as s:
        regions = (await s.execute(text("SELECT regions FROM events WHERE id = :e"), {"e": ev_id})).scalar_one()
    assert regions == ["IN", "IN-KA"], "the Karnataka page carrying it is the signal that it is a Karnataka story"
