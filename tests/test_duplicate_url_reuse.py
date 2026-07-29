"""The same article reaching us twice should be extracted once.

534 URL groups in production arrive more than once, 533 of them CROSS-source: the
same piece coming through a national feed and a regional one under different
external_ids. Dedupe keys on (source_id, external_id), so the URL is never
compared and both copies get a fulltext fetch AND a model call — 355 excess
enrichments, entirely wasted spend.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from enrichment.consumer import _extraction_for_same_url

pytestmark = pytest.mark.asyncio(loop_scope="session")

PAYLOAD = {"shared": {"headline_summary": "already extracted once"}}


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _enriched(s, url, tag, body="the body"):
    sid, rid, aid, eid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await s.execute(text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
                    {"i": str(sid), "s": f"src-{tag}-{sid.hex[:6]}"})
    await s.execute(
        text("INSERT INTO raw_items (id,source_id,external_id,url,title,raw,relevance) "
             "VALUES (:i,:s,:e,:u,'t','{}'::jsonb,'relevant')"),
        {"i": str(rid), "s": str(sid), "e": f"ext-{rid.hex[:8]}", "u": url},
    )
    await s.execute(
        text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
             "VALUES (:i,:r,:c,'body',2)"),
        {"i": str(aid), "r": str(rid), "c": body},
    )
    await s.execute(
        text("INSERT INTO enrichments (id,article_id,model,raw_model_output) "
             "VALUES (:i,:a,'ollama:test',CAST(:p AS jsonb))"),
        {"i": str(eid), "a": str(aid), "p": '{"shared": {"headline_summary": "already extracted once"}}'},
    )
    return sid, rid, aid, eid


async def _cleanup(made):
    async with session_scope() as s:
        for sid, rid, aid, eid in made:
            await s.execute(text("DELETE FROM field_provenance WHERE enrichment_id = :i"), {"i": str(eid)})
            await s.execute(text("DELETE FROM enrichments WHERE id = :i"), {"i": str(eid)})
            await s.execute(text("DELETE FROM articles WHERE id = :i"), {"i": str(aid)})
            await s.execute(text("DELETE FROM raw_items WHERE id = :i"), {"i": str(rid)})
            await s.execute(text("DELETE FROM sources WHERE id = :i"), {"i": str(sid)})


async def test_a_second_feed_carrying_the_same_url_reuses_the_extraction():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    url = f"https://example.test/{tag}/story"
    made = []
    try:
        async with session_scope() as s:
            made.append(await _enriched(s, url, tag, body="the shared body"))
        found = await _extraction_for_same_url(url)
        assert found is not None, "would have paid the model a second time"
        clean, payload, model = found
        assert clean == "the shared body"
        assert payload["shared"]["headline_summary"] == "already extracted once"
        assert model == "ollama:test"
    finally:
        await _cleanup(made)


async def test_a_url_we_have_never_seen_still_gets_extracted():
    """The guard must not swallow first sightings."""
    if not await _db_reachable():
        pytest.skip("no database")
    assert await _extraction_for_same_url(f"https://example.test/{uuid.uuid4().hex}/new") is None


async def test_a_missing_url_is_not_treated_as_a_match():
    """raw_items.url is nullable; NULL must not collide with NULL."""
    if not await _db_reachable():
        pytest.skip("no database")
    assert await _extraction_for_same_url(None) is None
    assert await _extraction_for_same_url("") is None


async def test_the_handler_does_not_call_the_model_for_a_url_it_already_extracted():
    """The one that matters. The tests above exercise the lookup in isolation, so
    they stay green even if the handler never calls it — which is exactly what a
    mutation proved: stubbing the wiring to `reused = None` left all of them
    passing while every duplicate went back to costing a model call.

    This asserts the spend, by failing if structured_chat is reached at all.
    """
    if not await _db_reachable():
        pytest.skip("no database")

    import enrichment.consumer as ec

    tag = uuid.uuid4().hex[:6]
    url = f"https://example.test/{tag}/twice"
    made = []
    calls = {"llm": 0, "fulltext": 0}

    async def _boom_llm(*a, **k):
        calls["llm"] += 1
        raise AssertionError("structured_chat called for an already-extracted URL")

    async def _boom_fulltext(*a, **k):
        calls["fulltext"] += 1
        raise AssertionError("retrieve_fulltext called for an already-extracted URL")

    async def _fake_embed(chunks):
        return [[0.0] * 768 for _ in chunks]

    orig = (ec.structured_chat, ec.retrieve_fulltext, ec.embed_texts)
    try:
        async with session_scope() as s:
            sid, rid, aid, eid = await _enriched(s, url, tag, body="the shared body")
            made.append((sid, rid, aid, eid))
            # A SECOND feed carrying the identical URL, not yet enriched.
            sid2, rid2 = uuid.uuid4(), uuid.uuid4()
            await s.execute(
                text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
                {"i": str(sid2), "s": f"second-{tag}"},
            )
            await s.execute(
                text("INSERT INTO raw_items (id,source_id,external_id,url,title,raw,relevance,classification) "
                     "VALUES (:i,:s,:e,:u,'t','{}'::jsonb,'relevant','{}'::jsonb)"),
                {"i": str(rid2), "s": str(sid2), "e": f"ext-{rid2.hex[:8]}", "u": url},
            )

        ec.structured_chat, ec.retrieve_fulltext, ec.embed_texts = _boom_llm, _boom_fulltext, _fake_embed
        await ec.handle_classified_item({"raw_item_id": str(rid2)})

        assert calls == {"llm": 0, "fulltext": 0}
        async with session_scope() as s:
            tier = (await s.execute(
                text("SELECT retrieval_tier FROM articles WHERE raw_item_id = :r"), {"r": str(rid2)}
            )).scalar()
        assert tier == "duplicate_url", f"second copy was not marked reused (tier={tier!r})"
    finally:
        ec.structured_chat, ec.retrieve_fulltext, ec.embed_texts = orig
        async with session_scope() as s:
            await s.execute(text("DELETE FROM article_chunks WHERE article_id IN "
                                 "(SELECT id FROM articles WHERE raw_item_id = :r)"), {"r": str(rid2)})
            await s.execute(text("DELETE FROM field_provenance WHERE enrichment_id IN "
                                 "(SELECT e.id FROM enrichments e JOIN articles a ON a.id = e.article_id "
                                 " WHERE a.raw_item_id = :r)"), {"r": str(rid2)})
            await s.execute(text("DELETE FROM enrichments WHERE article_id IN "
                                 "(SELECT id FROM articles WHERE raw_item_id = :r)"), {"r": str(rid2)})
            await s.execute(text("DELETE FROM articles WHERE raw_item_id = :r"), {"r": str(rid2)})
            await s.execute(text("DELETE FROM raw_items WHERE id = :i"), {"i": str(rid2)})
            await s.execute(text("DELETE FROM sources WHERE id = :i"), {"i": str(sid2)})
        await _cleanup(made)
