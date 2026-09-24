"""Every published version of a record is kept (migration e7a4c2b9f613).

What a reader read yesterday must be showable today: to a reader asking what
changed, to a complaint, to a regulator (IT Rules R19(3), 60 days). A trigger on
`events` keeps the version being replaced whenever what a reader reads changes,
and the last version when a record is deleted. Counts changing on every new
report are not a new version.
"""

import json
import uuid

import pytest
from sqlalchemy import text

from common.db import session_scope
from tests.test_projection_summary import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _revisions(eid):
    async with session_scope() as s:
        rows = (await s.execute(
            text("SELECT op, title, summary, lens_briefs FROM event_revisions WHERE event_id = :e ORDER BY id"),
            {"e": str(eid)},
        )).mappings().all()
    return [dict(r) for r in rows]


async def test_a_record_keeps_what_it_said_before_each_change():
    if not await _db_reachable():
        pytest.skip("no database")
    eid = uuid.uuid4()
    try:
        async with session_scope() as s:
            await s.execute(
                text("INSERT INTO events (id, title, summary, last_updated_at, projection) "
                     "VALUES (:i, 'Bridge closes', 'It closed.', now(), CAST(:p AS jsonb))"),
                {"i": str(eid), "p": json.dumps({"source_count": 1, "lens_briefs": {"reader": "First brief."}})},
            )
        # A new report arrives: counts change, nothing a reader reads does.
        async with session_scope() as s:
            await s.execute(text("UPDATE events SET projection = projection || '{\"source_count\": 2}'::jsonb WHERE id = :i"), {"i": str(eid)})
        assert await _revisions(eid) == [], "a count is not a new version of the record"

        # The brief is rewritten, then the headline corrected.
        async with session_scope() as s:
            await s.execute(text("UPDATE events SET projection = jsonb_set(projection, '{lens_briefs,reader}', '\"Second brief.\"') WHERE id = :i"), {"i": str(eid)})
        async with session_scope() as s:
            await s.execute(text("UPDATE events SET title = 'Bridge closes for repairs' WHERE id = :i"), {"i": str(eid)})
        revs = await _revisions(eid)
        assert [(r["op"], r["title"], r["lens_briefs"]["reader"]) for r in revs] == [
            ("update", "Bridge closes", "First brief."),
            ("update", "Bridge closes", "Second brief."),
        ]

        # Deleted: the last version it published is still kept.
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = :i"), {"i": str(eid)})
        last = (await _revisions(eid))[-1]
        assert (last["op"], last["title"], last["summary"]) == ("delete", "Bridge closes for repairs", "It closed.")
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM events WHERE id = :i"), {"i": str(eid)})
            await s.execute(text("DELETE FROM event_revisions WHERE event_id = :i"), {"i": str(eid)})
