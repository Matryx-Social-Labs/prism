"""A record lists the records the verifier judged earlier or later in its story.

Only links written on Jev's word at attach (event_links method 'verified'); the
LLM thread-linker's links stay off the page, as does anything merged away.
"""

import datetime as dt
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from api.main import app
from common.db import session_scope
from tests.test_verified_tier import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")
LONG_AGO = dt.datetime.now(dt.UTC) - dt.timedelta(days=60)  # out of the feed's way (test_geo)


@pytest_asyncio.fixture(loop_scope="session")
async def story():
    if not await _db_reachable():
        pytest.skip("no database")
    ids = {k: uuid.uuid4() for k in ("death", "strike", "probe", "thread_only")}
    async with session_scope() as s:
        for n, (k, eid) in enumerate(ids.items()):
            await s.execute(
                text("INSERT INTO events (id, title, summary, sector, first_seen_at, last_updated_at) "
                     "VALUES (:i, :t, 's', 'civic', :w, :w)"),
                {"i": str(eid), "t": f"{k} {eid.hex[:6]}", "w": LONG_AGO + dt.timedelta(hours=n)},
            )
        for a, b, method in (("death", "strike", "verified"), ("strike", "probe", "verified"),
                             ("strike", "thread_only", "thread")):
            await s.execute(
                text("INSERT INTO event_links (id, from_event_id, to_event_id, relation, confidence, method) "
                     "VALUES (:i, :f, :t, 'leads_to', 0.9, :m)"),
                {"i": str(uuid.uuid4()), "f": str(ids[a]), "t": str(ids[b]), "m": method},
            )
    yield ids
    async with session_scope() as s:
        await s.execute(text("DELETE FROM event_links WHERE from_event_id = ANY(CAST(:i AS uuid[]))"),
                        {"i": [str(v) for v in ids.values()]})
        await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:i AS uuid[]))"), {"i": [str(v) for v in ids.values()]})


async def test_a_record_lists_its_verified_earlier_and_later_developments(story):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        body = (await c.get(f"/api/v1/events/{story['strike']}")).json()
    assert [r["id"] for r in body["follow_ups"]["earlier"]] == [str(story["death"])]
    assert [r["id"] for r in body["follow_ups"]["later"]] == [str(story["probe"])], "a thread-linker link is not shown"


async def test_a_record_merged_away_is_not_listed(story):
    async with session_scope() as s:
        await s.execute(text("UPDATE events SET merged_into = :d WHERE id = :p"),
                        {"d": str(story["death"]), "p": str(story["probe"])})
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        body = (await c.get(f"/api/v1/events/{story['strike']}")).json()
    assert body["follow_ups"]["later"] == []


async def test_follow_ups_read_in_the_order_they_were_first_reported():
    """first_seen_at is when Prism processed a record; after a backlog that is
    the queue's order, not the story's (Flydubai, 2026-10-01)."""
    if not await _db_reachable():
        pytest.skip("no database")
    ids = {k: uuid.uuid4() for k in ("rescue", "praise", "award")}
    hours = dt.timedelta(hours=1)
    seen = {"rescue": LONG_AGO, "praise": LONG_AGO + hours, "award": LONG_AGO + 2 * hours}
    reported = {"rescue": LONG_AGO - 30 * hours, "praise": LONG_AGO - 2 * hours, "award": LONG_AGO - 8 * hours}
    async with session_scope() as s:
        for k, eid in ids.items():
            await s.execute(
                text("INSERT INTO events (id, title, summary, sector, first_seen_at, first_published_at, last_updated_at) "
                     "VALUES (:i, :t, 's', 'civic', :w, :p, :w)"),
                {"i": str(eid), "t": f"{k} {eid.hex[:6]}", "w": seen[k], "p": reported[k]},
            )
        for later in ("praise", "award"):
            await s.execute(
                text("INSERT INTO event_links (id, from_event_id, to_event_id, relation, confidence, method) "
                     "VALUES (:i, :f, :t, 'leads_to', 0.9, 'verified')"),
                {"i": str(uuid.uuid4()), "f": str(ids["rescue"]), "t": str(ids[later])},
            )
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
            body = (await c.get(f"/api/v1/events/{ids['rescue']}")).json()
        later = body["follow_ups"]["later"]
        assert [r["id"] for r in later] == [str(ids["award"]), str(ids["praise"])]
        assert later[0]["first_published_at"] == reported["award"].isoformat()
        assert body["first_published_at"] == reported["rescue"].isoformat()
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_links WHERE from_event_id = :r"), {"r": str(ids["rescue"])})
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:i AS uuid[]))"),
                            {"i": [str(v) for v in ids.values()]})
