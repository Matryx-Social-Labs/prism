"""Identical bodies are not one story when the headlines are unrelated.

Production 2026-09-27: every member of "Journalist Biography Profile" (event
73342608 — Bastar floods, khair smuggling, an ED chargesheet…) joined on the
embedding tier at score 1.000, because trafilatura had returned the same byline
bio for each; 97ba88e3 took 14 Madhya Pradesh stories and 0c3c1877 seven RBI
releases the same way. Text identity is evidence of one story only when the
headlines agree — the same article re-filed, or wire copy on two sites.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from correlation.clustering import find_event

pytestmark = pytest.mark.asyncio(loop_scope="session")

V = [1.0, 0.0] + [0.0] * 766
FOUNDER = "Paan's dark supply chain: How Rs 120-crore khair smuggling network spread its tentacles"


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _seed(tag: str):
    """An event whose embedding is V, founded by one article titled FOUNDER that
    names two specific actors — so both body-vector tiers could take a twin."""
    eid, sid, rid, aid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    ents = [(uuid.uuid4(), f"naidu-{tag}"), (uuid.uuid4(), f"bastar-police-{tag}")]
    async with session_scope() as s:
        await s.execute(text("INSERT INTO events (id,title,sector,last_updated_at,embedding) "
                             "VALUES (:i,'Journalist Biography Profile','politics',now(),CAST(:v AS vector))"),
                        {"i": str(eid), "v": "[" + ",".join(map(str, V)) + "]"})
        await s.execute(text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
                        {"i": str(sid), "s": f"ie-{tag}"})
        await s.execute(text("INSERT INTO raw_items (id,source_id,external_id,title,raw,relevance) "
                             "VALUES (:i,:s,:e,:t,'{}'::jsonb,'relevant')"),
                        {"i": str(rid), "s": str(sid), "e": f"ext-{tag}", "t": FOUNDER})
        await s.execute(text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
                             "VALUES (:i,:r,'bio','direct',1)"), {"i": str(aid), "r": str(rid)})
        await s.execute(text("INSERT INTO event_memberships (id,event_id,article_id,match_type,is_survivor) "
                             "VALUES (:i,:e,:a,'new_event',true)"),
                        {"i": str(uuid.uuid4()), "e": str(eid), "a": str(aid)})
        for ent_id, slug in ents:
            await s.execute(text("INSERT INTO entities (id,slug,name,entity_type) VALUES (:i,:s,:s,'person')"),
                            {"i": str(ent_id), "s": slug})
            await s.execute(text("INSERT INTO event_entities (id,event_id,entity_id,role) "
                                 "VALUES (:i,:e,:en,'subject')"),
                            {"i": str(uuid.uuid4()), "e": str(eid), "en": str(ent_id)})
            await s.execute(text("INSERT INTO article_entities (id,article_id,entity_id,role) "
                                 "VALUES (:i,:a,:en,'subject')"),
                            {"i": str(uuid.uuid4()), "a": str(aid), "en": str(ent_id)})
    return eid, sid, rid, aid, ents


async def _purge(eid, sid, rid, aid, ents):
    async with session_scope() as s:
        await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
        await s.execute(text("DELETE FROM event_entities WHERE event_id = :e"), {"e": str(eid)})
        await s.execute(text("DELETE FROM article_entities WHERE article_id = :a"), {"a": str(aid)})
        await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(aid)})
        await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(rid)})
        await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(sid)})
        await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"), {"i": [str(e[0]) for e in ents]})
        await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})


async def _find(title: str, slugs=None):
    async with session_scope() as s:
        return await find_event(s, cve_ids=[], url=None, title=title, published_at=None,
                                embedding=V, entity_slugs=slugs)


async def test_an_identical_body_under_an_unrelated_headline_does_not_merge():
    if not await _db_reachable():
        pytest.skip("no database")
    seeded = await _seed(uuid.uuid4().hex[:8])
    try:
        assert await _find("ED chargesheets EaseMyTrip promoter in Mahadev betting app case") is None
    finally:
        await _purge(*seeded)


async def test_nor_through_the_actors_extracted_from_that_same_body():
    """Refusing only the embedding tier hands the twin to entity_overlap, which
    scores the same zero distance plus the actors the extractor read out of the
    same bio — a merge "because the bodies are identical" all the same."""
    if not await _db_reachable():
        pytest.skip("no database")
    seeded = await _seed(uuid.uuid4().hex[:8])
    try:
        slugs = [e[1] for e in seeded[4]]
        assert await _find("ED chargesheets EaseMyTrip promoter in Mahadev betting app case", slugs) is None
    finally:
        await _purge(*seeded)


async def test_an_identical_body_under_its_own_headline_still_merges():
    """The same story re-filed under a second URL with a reworded headline."""
    if not await _db_reachable():
        pytest.skip("no database")
    seeded = await _seed(uuid.uuid4().hex[:8])
    try:
        m = await _find("Rs 120-crore khair smuggling network: how the paan supply chain spread")
        assert m is not None and m.match_type == "embedding" and m.event_id == seeded[0]
    finally:
        await _purge(*seeded)
