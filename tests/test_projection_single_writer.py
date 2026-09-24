"""The projection rebuild never erases a brief it did not write (audit H11).

`events.projection` has two writers: the correlation rebuild (coverage, counts,
lens facts) and persist_briefs (lens_briefs / lens_points, from the analysis
pass, the extractor and the API's on-demand lens brief). The rebuild used to read
the projection, keep the briefs it saw, and write the whole object back, so a
brief committed between that read and that write was lost and the next reader
paid for it again. Pinned by committing a brief exactly there.
"""

import uuid
from contextlib import asynccontextmanager

import pytest
from sqlalchemy import text

import correlation.consumer as consumer
from common.db import session_scope
from correlation.briefs import persist_briefs
from tests.test_projection_summary import _add_member, _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_a_brief_committed_mid_rebuild_survives_it(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")

    eid, src = uuid.uuid4(), uuid.uuid4()
    created = []
    try:
        async with session_scope() as s:
            await s.execute(
                text("INSERT INTO sources (id, slug, name, source_type, country, publisher) "
                     "VALUES (:i, :s, 'Writer Test', 'rss', 'IN', 'writer-test')"),
                {"i": str(src), "s": f"writer-{eid.hex[:8]}"},
            )
            await s.execute(
                text("INSERT INTO events (id, title, summary, sector, regions, last_updated_at, projection) "
                     "VALUES (:i, 'Bridge closes', 'It closed.', 'politics', CAST(:r AS text[]), now(), "
                     "CAST(:p AS jsonb))"),
                {"i": str(eid), "r": ["IN"], "p": '{"lens_briefs": {"reader": "The first brief."}}'},
            )
            created.append(await _add_member(s, eid, title="Bridge closes", summary="It closed.", source_id=src))

        # Between the rebuild's read of the event and its write, another writer
        # (the API serving an on-demand lens) commits a brief in its own session.
        real_scope = consumer.session_scope

        @asynccontextmanager
        async def racing_scope():
            async with real_scope() as session:
                real_get = session.get

                async def get_then_race(model, ident, *a, **kw):
                    row = await real_get(model, ident, *a, **kw)
                    await persist_briefs(eid, {"markets": {"text": "Written meanwhile.", "points": ["A point."]}})
                    return row

                session.get = get_then_race
                yield session

        monkeypatch.setattr(consumer, "session_scope", racing_scope)
        await consumer._rebuild_projection(eid)

        async with session_scope() as s:
            proj = (await s.execute(text("SELECT projection FROM events WHERE id = :i"), {"i": str(eid)})).scalar_one()
        assert proj["lens_briefs"] == {"reader": "The first brief.", "markets": "Written meanwhile."}, (
            "the rebuild wrote back the briefs it read and erased one committed meanwhile"
        )
        assert proj["lens_points"] == {"markets": ["A point."]}
        # And it still did its own job.
        assert proj["source_count"] == 1 and proj["coverage"]["origins"] == {"IN": 1}
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_memberships WHERE event_id = :e"), {"e": str(eid)})
            for raw_id, art_id in created:
                await s.execute(text("DELETE FROM enrichments WHERE article_id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM articles WHERE id = :a"), {"a": str(art_id)})
                await s.execute(text("DELETE FROM raw_items WHERE id = :r"), {"r": str(raw_id)})
            await s.execute(text("DELETE FROM events WHERE id = :e"), {"e": str(eid)})
            await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(src)})
