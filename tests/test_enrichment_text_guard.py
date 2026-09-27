"""Enrichment refuses boilerplate text and model commentary, through the real handler.

Production 2026-09-27: 14 Indian Express stories by one reporter all arrived as
her byline bio, embedded to one vector and became one event; the extractor then
summarised the bio ("The provided text contains the biographical profile of a
journalist and does not report on…") and that summary led the front page.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import enrichment.consumer as ec
from common.db import session_scope
from enrichment.schemas import ArticleExtraction

pytestmark = pytest.mark.asyncio(loop_scope="session")

BIO = (
    "Anand Mohan J is an award-winning Senior Correspondent for The Indian Express, currently leading "
    "coverage of Madhya Pradesh from Bhopal. He reports on governance, wildlife and rural distress, and "
    "has written on the cheetah reintroduction at Kuno since its first release. ... Read More"
)
STORY_TITLE = "Madhya Pradesh CM wields pickaxe in Ujjain to pull down own home for Simhastha"
FEED_BODY = "The chief minister joined the demolition drive in Ujjain ahead of the Simhastha fair."


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _source(s, tag):
    sid = uuid.uuid4()
    await s.execute(text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
                    {"i": str(sid), "s": f"guard-{tag}"})
    return sid


async def _raw(s, sid, url, title, body=None):
    rid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO raw_items (id,source_id,external_id,url,url_canonical,title,body,raw,relevance,"
             "classification) VALUES (:i,:s,:e,:u,:u,:t,:b,'{}'::jsonb,'relevant','{}'::jsonb)"),
        {"i": str(rid), "s": str(sid), "e": f"ext-{rid.hex[:8]}", "u": url, "t": title, "b": body},
    )
    return rid


async def _article(s, rid, body):
    await s.execute(
        text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
             "VALUES (:i,:r,:c,'direct',30)"),
        {"i": str(uuid.uuid4()), "r": str(rid), "c": body},
    )


async def _purge(sid):
    async with session_scope() as s:
        arts = "SELECT a.id FROM articles a JOIN raw_items ri ON ri.id = a.raw_item_id WHERE ri.source_id = :s"
        await s.execute(text(f"DELETE FROM field_provenance WHERE enrichment_id IN "
                             f"(SELECT id FROM enrichments WHERE article_id IN ({arts}))"), {"s": str(sid)})
        await s.execute(text(f"DELETE FROM enrichments WHERE article_id IN ({arts})"), {"s": str(sid)})
        await s.execute(text(f"DELETE FROM article_chunks WHERE article_id IN ({arts})"), {"s": str(sid)})
        await s.execute(text(f"DELETE FROM articles WHERE id IN ({arts})"), {"s": str(sid)})
        await s.execute(text("DELETE FROM raw_items WHERE source_id = :s"), {"s": str(sid)})
        await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(sid)})


def _stub_pipeline(monkeypatch, fetched: str, summary: str = "The chief minister joined a demolition drive."):
    seen = {}

    async def _fulltext(url, body, title=None):
        return fetched, "direct", None

    async def _chat(*, messages, **kw):
        seen["prompt"] = str(messages)
        return ArticleExtraction.model_validate({"shared": {"headline_summary": summary}})

    async def _embed(chunks):
        return [[0.0] * 768 for _ in chunks]

    async def _publish(*a, **k):
        seen["published"] = True

    monkeypatch.setattr(ec, "retrieve_fulltext", _fulltext)
    monkeypatch.setattr(ec, "structured_chat", _chat)
    monkeypatch.setattr(ec, "embed_texts", _embed)
    monkeypatch.setattr(ec.stream, "publish", _publish)
    return seen


async def _stored(rid):
    async with session_scope() as s:
        return (await s.execute(
            text("SELECT ri.relevance, ri.rejection_reason, a.clean_text, a.retrieval_tier FROM raw_items ri "
                 "LEFT JOIN articles a ON a.raw_item_id = ri.id WHERE ri.id = :r"), {"r": str(rid)},
        )).mappings().one()


async def test_a_bio_already_seen_under_another_url_on_the_site_falls_back_to_the_feed_body(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    async with session_scope() as s:
        sid = await _source(s, tag)
        first = await _raw(s, sid, f"https://example.test/{tag}/cheetah", "Eye on second baby boom at Kuno")
        await _article(s, first, BIO)
        rid = await _raw(s, sid, f"https://example.test/{tag}/pickaxe", STORY_TITLE, FEED_BODY)
    seen = _stub_pipeline(monkeypatch, BIO)
    try:
        await ec.handle_classified_item({"raw_item_id": str(rid)})
        row = await _stored(rid)
        assert (row["clean_text"], row["retrieval_tier"]) == (FEED_BODY, "body")
        assert "Anand Mohan" not in seen["prompt"], "the extractor was shown the bio"
    finally:
        await _purge(sid)


async def test_the_same_story_refiled_under_a_second_url_keeps_its_text(monkeypatch):
    """prajavani re-files a story under a new URL and a new headline; its lead
    restates the headline, so the repeat is the story, not boilerplate."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    story = ("Madhya Pradesh chief minister wields a pickaxe in Ujjain to pull down his own home for the "
             "Simhastha fair, officials said. ") * 4
    async with session_scope() as s:
        sid = await _source(s, tag)
        first = await _raw(s, sid, f"https://example.test/{tag}/a", "CM demolishes own house in Ujjain")
        await _article(s, first, story)
        rid = await _raw(s, sid, f"https://example.test/{tag}/b", STORY_TITLE, FEED_BODY)
    _stub_pipeline(monkeypatch, story)
    try:
        await ec.handle_classified_item({"raw_item_id": str(rid)})
        row = await _stored(rid)
        assert (row["clean_text"], row["retrieval_tier"]) == (story, "direct")
    finally:
        await _purge(sid)


async def test_the_same_bio_on_another_site_is_not_this_sites_boilerplate(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    async with session_scope() as s:
        other = await _source(s, tag + "o")
        first = await _raw(s, other, f"https://other.test/{tag}/x", "Eye on second baby boom at Kuno")
        await _article(s, first, BIO)
        sid = await _source(s, tag)
        rid = await _raw(s, sid, f"https://example.test/{tag}/pickaxe", STORY_TITLE, FEED_BODY)
    _stub_pipeline(monkeypatch, BIO)
    try:
        await ec.handle_classified_item({"raw_item_id": str(rid)})
        assert (await _stored(rid))["retrieval_tier"] == "direct"
    finally:
        await _purge(sid)
        await _purge(other)


async def test_model_commentary_is_not_news_and_is_never_stored(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    async with session_scope() as s:
        sid = await _source(s, tag)
        rid = await _raw(s, sid, f"https://example.test/{tag}/pickaxe", STORY_TITLE, FEED_BODY)
    seen = _stub_pipeline(
        monkeypatch, FEED_BODY * 6,
        summary="The provided text contains the biographical profile of a journalist and does not report on "
                "any demolition.",
    )
    try:
        await ec.handle_classified_item({"raw_item_id": str(rid)})
        row = await _stored(rid)
        assert row["relevance"] == "rejected"
        assert "commentary" in row["rejection_reason"]
        assert row["clean_text"] is None, "an article row was written for a non-news extraction"
        assert "published" not in seen, "it was handed on to correlation"
    finally:
        await _purge(sid)
