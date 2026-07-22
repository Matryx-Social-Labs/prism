"""Canonical story timeline — the connected component over STRONG edges.

A strong edge = two events sharing >=2 distinctive actors. The story is the
transitive component, so a leaf development reaches the whole story via its hub;
an event sharing only ONE actor (a weak/magnet-only link) stays out. This is what
fixes the "6 thread nodes on a hub, 1 on a leaf" collapse and keeps unrelated
stories (a tariff story sharing only "Trump") off the timeline.

    s1 ==(a1,a2)== s2 ==(a3,a4)== s3       strong chain → all one story
    s1 --(a1)-- noise                       one shared actor → excluded
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from correlation.threads import story_timeline

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def test_story_timeline_transitive_strong_component():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    s1, s2, s3, noise = (uuid.uuid4() for _ in range(4))
    actors = {k: uuid.uuid4() for k in ("a1", "a2", "a3", "a4")}
    # edges: s1-s2 share {a1,a2} (strong); s2-s3 share {a3,a4} (strong);
    #        s1-s3 share nothing; noise-s1 share {a1} only (weak).
    membership = [
        (s1, "a1"), (s1, "a2"),
        (s2, "a1"), (s2, "a2"), (s2, "a3"), (s2, "a4"),
        (s3, "a3"), (s3, "a4"),
        (noise, "a1"),
    ]
    try:
        async with session_scope() as s:
            for eid in (s1, s2, s3, noise):
                await s.execute(
                    text("INSERT INTO events (id,title,sector,last_updated_at) VALUES (:i,:t,'politics',now())"),
                    {"i": str(eid), "t": f"dev {eid}"},
                )
            for k, ent in actors.items():
                await s.execute(
                    text("INSERT INTO entities (id,slug,name,entity_type) VALUES (:i,:s,:n,'person')"),
                    {"i": str(ent), "s": f"{k}-{tag}", "n": f"{k}-{tag}"},
                )
            for eid, k in membership:
                await s.execute(
                    text("INSERT INTO event_entities (id,event_id,entity_id,role) VALUES (:i,:e,:en,'subject')"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "en": str(actors[k])},
                )

        # From the LEAF (s3), the whole story should be reachable transitively.
        r = await story_timeline(s3)
        ids = {d["id"] for d in r["developments"]}
        assert {str(s1), str(s2), str(s3)} <= ids  # transitive component
        assert str(noise) not in ids  # one shared actor → weak → excluded
        cur = [d for d in r["developments"] if d["is_current"]]
        assert len(cur) == 1 and cur[0]["id"] == str(s3)  # "you are here" on the seed
        # Same story from any member — s1 yields the same three.
        r1 = await story_timeline(s1)
        assert {d["id"] for d in r1["developments"]} >= {str(s1), str(s2), str(s3)}
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_entities WHERE event_id = ANY(:e)"),
                            {"e": [str(s1), str(s2), str(s3), str(noise)]})
            await s.execute(text("DELETE FROM entities WHERE id = ANY(:i)"),
                            {"i": [str(a) for a in actors.values()]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(:e)"),
                            {"e": [str(s1), str(s2), str(s3), str(noise)]})
