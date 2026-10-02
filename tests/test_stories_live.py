"""Turning the persistent stories live (tools/stories_live): every judge-built
story lists its records, and a Leiden story whose records sit at least half in
one judge-built story redirects there, so an old shared link opens the new
story. --revert undoes both."""

import uuid

import pytest
from sqlalchemy import text

from common.db import session_scope
from tests.test_stories import _story_of_records
from tests.test_verified_tier import _db_reachable, _direction, _event_with_member
from tools import stories_live

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _leiden(s, members: list[uuid.UUID]) -> uuid.UUID:
    sid = uuid.uuid4()
    await s.execute(text("INSERT INTO stories (id, slug, label, \"cast\", member_event_ids, status) VALUES "
                         "(:i, :sl, 'Leiden', '[]'::jsonb, CAST(:m AS jsonb), 'active')"),
                    {"i": str(sid), "sl": f"fx-{sid.hex[:12]}", "m": "[" + ",".join(f'"{m}"' for m in members) + "]"})
    return sid


async def test_go_live_lists_records_redirects_majority_leiden_stories_and_reverts():
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:6]
    async with session_scope() as s:
        recs = [await _event_with_member(s, f"Flydubai {k} {tag}", _direction()) for k in range(4)]
        v3 = await _story_of_records(s, recs[:2])
        await s.execute(text("UPDATE stories SET status = 'shadow', member_event_ids = '[]'::jsonb WHERE id = :i"),
                        {"i": str(v3)})
        half = await _leiden(s, [recs[0], recs[1], recs[2], recs[3]])  # 2 of 4 in the v3 story: redirects
        minority = await _leiden(s, [recs[0], recs[2], recs[3]])  # 1 of 3: stays
        journal: dict = {}
        await stories_live.go_live(s, journal)
        row = (await s.execute(text("SELECT status, member_event_ids FROM stories WHERE id = :i"), {"i": str(v3)})).one()
        assert row.status != "shadow" and set(row.member_event_ids) == {str(recs[0]), str(recs[1])}
        moved = dict((await s.execute(text("SELECT id, merged_into FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                                      {"i": [str(half), str(minority)]})).all())
        assert moved == {half: v3, minority: None}
        await stories_live.revert(s, journal)
        back = dict((await s.execute(text("SELECT id, status FROM stories WHERE id = ANY(CAST(:i AS uuid[]))"),
                                     {"i": [str(v3), str(half)]})).all())
        assert back == {v3: "shadow", half: "active"}
        assert (await s.execute(text("SELECT merged_into FROM stories WHERE id = :i"), {"i": str(half)})).scalar_one() is None
        await s.rollback()
