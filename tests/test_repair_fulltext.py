"""tools/repair --fulltext against a real database: what it deletes, dissolves and keeps.

The repair re-uses the pipeline: a bad article is deleted and its raw item left
'relevant' so the worker's stalled-item sweep re-enriches it through the guarded
fetch. An event founded by bad text and made mostly of it is dissolved; one that
is mostly real reporting keeps its id and loses only the bad members.
"""

import os
import re
import uuid

import asyncpg
import pytest

from tools.repair import apply_fulltext, report_fulltext

pytestmark = pytest.mark.asyncio(loop_scope="session")

BIO = ("Anish Mondal is a journalist with over nine years of experience covering the railways and urban "
       "transport for The Indian Express. He has reported on rolling stock, fares and passenger amenities. "
       "... Read More")
STORIES = [
    # The founder's headline shares words with the bio (97ba88e3: "Madhya Pradesh"),
    # so only the per-opening rule catches it.
    "Railways revises fares and passenger amenities on rolling stock for urban transport",
    "Kanpur Central-Anand Vihar Terminal Express train approved: check route and stops",
    "Bhuj-Barauni Amrit Bharat train approved: check route, stops, timings and frequency",
    "BEML secures Rs 5,400 crore order for Mumbai-Ahmedabad bullet train project",
]
V = "[" + ",".join(["1"] + ["0"] * 767) + "]"
W = "[" + ",".join(["0", "1"] + ["0"] * 766) + "]"


def _dsn() -> str:
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", os.environ.get("DATABASE_URL", ""))


async def _connect():
    try:
        return await asyncpg.connect(_dsn(), timeout=10)
    except (OSError, asyncpg.PostgresError, ValueError):
        return None


async def _member(c, sid, eid, title, text, rank, summary="A report."):
    rid, aid = uuid.uuid4(), uuid.uuid4()
    url = f"https://example.test/{rid.hex}"
    await c.execute("INSERT INTO raw_items (id,source_id,external_id,url,title,raw,relevance) "
                    "VALUES ($1,$2,$3,$4,$5,'{}'::jsonb,'relevant')", rid, sid, rid.hex, url, title)
    await c.execute("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
                    "VALUES ($1,$2,$3,'direct',40)", aid, rid, text)
    await c.execute("INSERT INTO enrichments (id,article_id,model,summary,shared_fields) "
                    "VALUES ($1,$2,'test',$3,'{}'::jsonb)", uuid.uuid4(), aid, summary)
    await c.execute("INSERT INTO article_chunks (id,article_id,chunk_index,text,embedding) "
                    "VALUES ($1,$2,0,$3,$4::vector)", uuid.uuid4(), aid, text[:1200], W if rank else V)
    await c.execute("INSERT INTO event_memberships (id,event_id,article_id,match_type,is_survivor,created_at) "
                    "VALUES ($1,$2,$3,$4,$5, now() + make_interval(secs => $6))",
                    uuid.uuid4(), eid, aid, "embedding" if rank else "new_event", rank == 0, rank)
    return rid, aid


async def _event(c, title):
    eid = uuid.uuid4()
    await c.execute("INSERT INTO events (id,title,summary,sector,last_updated_at,embedding,projection) "
                    "VALUES ($1,$2,'The bio.','politics',now(),$3::vector,"
                    "'{\"source_slugs\": [\"x\"], \"source_count\": 9}'::jsonb)", eid, title, V)
    return eid


async def test_the_repair_dissolves_a_bio_event_and_keeps_a_real_one():
    c = await _connect()
    if c is None:
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    sid = uuid.uuid4()
    try:
        await c.execute("INSERT INTO sources (id,slug,name,source_type) VALUES ($1,$2,$2,'rss')", sid, f"ie-{tag}")
        # 1. Four railway stories that all arrived as the reporter's bio.
        bio_ev = await _event(c, "Journalist Biography Profile")
        bios = [await _member(c, sid, bio_ev, t, BIO, i) for i, t in enumerate(STORIES)]
        # A real report that title-matched into it: detached, kept, re-correlated by the sweep.
        _good_rid, good_aid = await _member(
            c, sid, bio_ev, "Railways revises fares and amenities for passengers from October",
            "Indian Railways revised fares and passenger amenities from October, the ministry said. " * 5, 9)
        # 2. A real story whose founder was the bio page of a re-titled URL, and
        #    three real reports: kept, re-founded on its first real report.
        real_ev = await _event(c, "Delhi Metro shuts 16 stations for Independence Day")
        await _member(c, sid, real_ev, "Commuters told to plan ahead as security tightens on Delhi Metro network",
                      BIO, 0)
        report = "Delhi Metro will shut 16 stations for Independence Day security, officials said. " * 5
        for i in range(3):
            await _member(c, sid, real_ev, "Delhi Metro to shut 16 stations for Independence Day",
                          report, i + 1, summary=f"Metro shuts stations ({i}).")

        plan = await report_fulltext(c)
        assert bio_ev in {uuid.UUID(e) for e in plan["dissolve"]}
        assert real_ev in {uuid.UUID(e) for e in plan["refound"]}
        await apply_fulltext(c, plan)

        # The bad articles are gone and their raw items wait for the requeue sweep.
        for rid, aid in bios:
            assert await c.fetchval("SELECT count(*) FROM articles WHERE id = $1", aid) == 0
            assert await c.fetchval("SELECT relevance FROM raw_items WHERE id = $1", rid) == "relevant"
        ev = await c.fetchrow("SELECT embedding, projection FROM events WHERE id = $1", bio_ev)
        assert ev["embedding"] is None
        assert '"source_slugs": []' in ev["projection"]
        assert await c.fetchval("SELECT count(*) FROM event_memberships WHERE event_id = $1", bio_ev) == 0
        assert await c.fetchval("SELECT count(*) FROM articles WHERE id = $1", good_aid) == 1, (
            "a real report was deleted with the bio event")

        real = await c.fetchrow("SELECT summary, projection FROM events WHERE id = $1", real_ev)
        assert real["summary"] == "Metro shuts stations (0)."
        assert '"source_count": 1' in real["projection"], "three reports from one masthead are one outlet"
        assert await c.fetchval("SELECT count(*) FROM event_memberships WHERE event_id = $1", real_ev) == 3
    finally:
        arts = "SELECT a.id FROM articles a JOIN raw_items ri ON ri.id = a.raw_item_id WHERE ri.source_id = $1"
        await c.execute(f"DELETE FROM event_memberships WHERE article_id IN ({arts})", sid)
        await c.execute(f"DELETE FROM enrichments WHERE article_id IN ({arts})", sid)
        await c.execute(f"DELETE FROM article_chunks WHERE article_id IN ({arts})", sid)
        await c.execute(f"DELETE FROM articles WHERE id IN ({arts})", sid)
        await c.execute("DELETE FROM raw_items WHERE source_id = $1", sid)
        await c.execute("DELETE FROM sources WHERE id = $1", sid)
        await c.execute("DELETE FROM events WHERE title IN ('Journalist Biography Profile', "
                        "'Delhi Metro shuts 16 stations for Independence Day')")
        await c.close()
