"""The public corrections log and a record's earlier versions.

Pinned: a correction shows on the record and on /corrections, newest first; a
version serves only the FREE text (a paid lens stays paid in its history); the
table refuses a reason outside the two editorial ones and a note too short to
tell a reader anything; a correction outlives its record.
"""

import json
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from common.db import session_scope
from tests.test_projection_summary import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")


def _client():
    from api.main import app

    return AsyncClient(transport=ASGITransport(app=app), base_url="http://t")


async def test_versions_serve_the_free_text_only_and_corrections_list_newest_first():
    if not await _db_reachable():
        pytest.skip("no database")
    eid = uuid.uuid4()
    try:
        async with session_scope() as s:
            await s.execute(
                text("INSERT INTO events (id, title, summary, last_updated_at, projection) VALUES (:i, 'Old headline', 's', now(), CAST(:p AS jsonb))"),
                {"i": str(eid), "p": json.dumps({"lens_briefs": {"reader": "Free brief.", "markets": "Paid read."}})},
            )
        async with session_scope() as s:
            await s.execute(text("UPDATE events SET title = 'New headline' WHERE id = :i"), {"i": str(eid)})
            await s.execute(text("INSERT INTO event_corrections (event_id, reason, note, actor, created_at) VALUES "
                                 "(:i, 'source_correction', 'The outlet corrected the toll from 14 to 12.', 'f', now() - interval '1 hour'), "
                                 "(:i, 'prism_error', 'The headline named the wrong district; fixed.', 'f', now())"), {"i": str(eid)})
        async with _client() as c:
            v = (await c.get(f"/api/v1/events/{eid}/versions")).json()
            log = (await c.get("/api/v1/corrections?limit=500")).json()["corrections"]
        assert v["versions"][0]["title"] == "Old headline" and v["versions"][0]["brief"] == "Free brief."
        assert "Paid read." not in json.dumps(v), "a paid lens stays paid in its history"
        assert [x["reason"] for x in v["corrections"]] == ["prism_error", "source_correction"]
        mine = [x for x in log if x["event_id"] == str(eid)]
        assert [x["reason"] for x in mine] == ["prism_error", "source_correction"] and mine[0]["title"] == "New headline"

        # Deleted: the correction and its last title survive.
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = :i"), {"i": str(eid)})
        async with _client() as c:
            log = (await c.get("/api/v1/corrections?limit=500")).json()["corrections"]
        assert [x["title"] for x in log if x["event_id"] == str(eid)] == ["New headline", "New headline"]
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = :i"), {"i": str(eid)})
            await s.execute(text("DELETE FROM event_corrections WHERE event_id = :i"), {"i": str(eid)})
            await s.execute(text("DELETE FROM event_revisions WHERE event_id = :i"), {"i": str(eid)})


@pytest.mark.parametrize("reason,note", [("opinion", "A reason nobody defined for this."), ("prism_error", "short")])
async def test_the_table_refuses_an_undefined_reason_or_an_empty_note(reason, note):
    if not await _db_reachable():
        pytest.skip("no database")
    with pytest.raises(IntegrityError):
        async with session_scope() as s:
            await s.execute(text("INSERT INTO event_corrections (event_id, reason, note, actor) VALUES (:i, :r, :n, 'f')"),
                            {"i": str(uuid.uuid4()), "r": reason, "n": note})
