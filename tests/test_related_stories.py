"""A story's related stories, and the statement timeout every API request runs under.

The related-stories query once cast link ids to text and probed every story with
jsonb `?` per link; on a 3,699-member story it ran for over an hour, a copy per
visit, until /dev/shm filled and every query failed (2026-10-16). These pin what
the faster form must still return, and that no API query can run unbounded."""

import datetime as dt
import json
import uuid

import pytest
from sqlalchemy import text

from api.routes.trending import _related_stories
from common.db import API_STATEMENT_TIMEOUT, get_db, session_scope
from tests.test_verified_tier import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")
LONG_AGO = dt.datetime.now(dt.UTC) - dt.timedelta(days=60)


async def test_causal_links_in_either_direction_relate_active_stories_only():
    if not await _db_reachable():
        pytest.skip("no database")
    ev = {k: uuid.uuid4() for k in ("a1", "a2", "later", "dormant", "earlier", "unrelated")}
    stories = {  # name: (status, members)
        "subject": ("active", ["a1", "a2"]),
        "later": ("active", ["later"]),
        "dormant": ("dormant", ["dormant"]),
        "earlier": ("active", ["earlier"]),
        "unrelated": ("active", ["unrelated"]),
    }
    sid = {k: uuid.uuid4() for k in stories}
    tag = uuid.uuid4().hex[:6]
    async with session_scope() as s:
        for k, eid in ev.items():
            await s.execute(
                text("INSERT INTO events (id, title, summary, sector, first_seen_at, last_updated_at) "
                     "VALUES (:i, :t, 's', 'civic', :w, :w)"),
                {"i": str(eid), "t": f"{k} {tag}", "w": LONG_AGO},
            )
        for f, t, rel in (("a1", "later", "leads_to"), ("a2", "dormant", "leads_to"),
                          ("earlier", "a2", "leads_to"), ("a1", "unrelated", "none")):
            await s.execute(
                text("INSERT INTO event_links (id, from_event_id, to_event_id, relation, confidence, method) "
                     "VALUES (:i, :f, :t, :r, 0.9, 'verified')"),
                {"i": str(uuid.uuid4()), "f": str(ev[f]), "t": str(ev[t]), "r": rel},
            )
        for k, (status, members) in stories.items():
            await s.execute(
                text('INSERT INTO stories (id, slug, label, "cast", member_event_ids, status) '
                     "VALUES (:i, :s, :s, '[]'::jsonb, CAST(:m AS jsonb), :st)"),
                {"i": str(sid[k]), "s": f"{k}-{tag}", "m": json.dumps([str(ev[m]) for m in members]), "st": status},
            )
    try:
        async with session_scope() as s:
            related = await _related_stories(s, sid["subject"], [ev["a1"], ev["a2"]], [])
        assert {r["slug"] for r in related} == {f"later-{tag}", f"earlier-{tag}"}
        assert all(r["causal"] for r in related)
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"), {"i": [str(v) for v in sid.values()]})
            await s.execute(text("DELETE FROM event_links WHERE from_event_id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(v) for v in ev.values()]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:i AS uuid[]))"), {"i": [str(v) for v in ev.values()]})


async def test_api_requests_run_under_a_statement_timeout():
    if not await _db_reachable():
        pytest.skip("no database")
    gen = get_db()
    db = await anext(gen)
    try:
        assert (await db.execute(text("SHOW statement_timeout"))).scalar() == API_STATEMENT_TIMEOUT
    finally:
        await gen.aclose()
