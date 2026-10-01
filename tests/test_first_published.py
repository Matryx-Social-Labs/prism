"""A record is dated by when it was first reported, and its links run forward.

Measured on production 2026-10-01: the Flydubai cockpit-attack story (190
articles published 09-30 07:30 to 10-01 12:10 UTC) became 70 records, all first
seen 10-01 08:18-12:14, because a backlog drained in the queue's order. Every
timeline ordered by first_seen_at read in processing order, and 515 of 2,668
thread links ran from the later record to the earlier one.

Fixtures are dated 60 days back (out of the feed's way, test_geo) and removed.
"""

import datetime as dt
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text

import correlation.chronology as chronology
import correlation.threads as threads
from common.config import get_settings
from common.db import session_scope
from common.models import Event
from correlation.consumer import _link_follow_up, _rebuild_projection
from correlation.schemas import ThreadLinkJudgement, ThreadLinkResult
from tests.test_verified_tier import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")

SEEN = (dt.datetime.now(dt.UTC) - dt.timedelta(days=60)).replace(microsecond=0)
H = dt.timedelta(hours=1)


class World:
    """Records and their reports, as correlation writes them, and their removal."""

    def __init__(self):
        self.source = uuid.uuid4()
        self.events: list[uuid.UUID] = []
        self.raw: list[uuid.UUID] = []
        self.articles: list[uuid.UUID] = []

    async def record(self, s, title: str, *, seen=SEEN) -> uuid.UUID:
        eid = uuid.uuid4()
        await s.execute(
            text("INSERT INTO events (id, title, summary, sector, first_seen_at, last_updated_at) "
                 "VALUES (:i, :t, 's', 'civic', :w, :w)"),
            {"i": str(eid), "t": f"{title} {eid.hex[:6]}", "w": seen},
        )
        self.events.append(eid)
        return eid

    async def report(self, s, eid: uuid.UUID, published, *, founder: bool = False) -> uuid.UUID:
        rid, aid = uuid.uuid4(), uuid.uuid4()
        await s.execute(
            text("INSERT INTO raw_items (id, source_id, external_id, title, raw, relevance, published_at) "
                 "VALUES (:i, :s, :x, 'report', '{}'::jsonb, 'relevant', :p)"),
            {"i": str(rid), "s": str(self.source), "x": str(rid), "p": published},
        )
        await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                             "VALUES (:i, :r, 'body', 'rss', 1)"), {"i": str(aid), "r": str(rid)})
        await s.execute(text("INSERT INTO enrichments (id, article_id, summary, event_type) "
                             "VALUES (:i, :a, 's', 'report')"), {"i": str(uuid.uuid4()), "a": str(aid)})
        if eid is not None:
            await s.execute(
                text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                     "VALUES (:i, :e, :a, :m, :f)"),
                {"i": str(uuid.uuid4()), "e": str(eid), "a": str(aid),
                 "m": "new_event" if founder else "entity_overlap", "f": founder},
            )
        self.raw.append(rid)
        self.articles.append(aid)
        return aid

    async def remove(self):
        ev, ar = [str(e) for e in self.events], [str(a) for a in self.articles]
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_links WHERE from_event_id = ANY(CAST(:e AS uuid[])) "
                                 "OR to_event_id = ANY(CAST(:e AS uuid[]))"), {"e": ev})
            await s.execute(text("DELETE FROM event_match_verdicts WHERE article_id = ANY(CAST(:a AS uuid[]))"), {"a": ar})
            await s.execute(text("DELETE FROM event_memberships WHERE article_id = ANY(CAST(:a AS uuid[]))"), {"a": ar})
            await s.execute(text("DELETE FROM enrichments WHERE article_id = ANY(CAST(:a AS uuid[]))"), {"a": ar})
            await s.execute(text("DELETE FROM articles WHERE id = ANY(CAST(:a AS uuid[]))"), {"a": ar})
            await s.execute(text("DELETE FROM raw_items WHERE id = ANY(CAST(:r AS uuid[]))"),
                            {"r": [str(r) for r in self.raw]})
            await s.execute(text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"), {"e": ev})
            await s.execute(text("DELETE FROM sources WHERE id = :s"), {"s": str(self.source)})


@pytest_asyncio.fixture(loop_scope="session")
async def world():
    if not await _db_reachable():
        pytest.skip("no database")
    w = World()
    async with session_scope() as s:
        await s.execute(text("INSERT INTO sources (id, slug, name, source_type) VALUES (:i, :s, 'fixture', 'rss')"),
                        {"i": str(w.source), "s": f"fixture-{w.source.hex[:8]}"})
    yield w
    await w.remove()


async def _published(eid) -> dt.datetime | None:
    async with session_scope() as s:
        return (await s.execute(text("SELECT first_published_at FROM events WHERE id = :e"), {"e": str(eid)})).scalar()


async def _links(*eids) -> set[tuple]:
    async with session_scope() as s:
        rows = (await s.execute(
            text("SELECT from_event_id, to_event_id FROM event_links "
                 "WHERE from_event_id = ANY(CAST(:e AS uuid[])) AND relation = 'leads_to'"),
            {"e": [str(e) for e in eids]},
        )).all()
    return {(r[0], r[1]) for r in rows}


async def _link(f, t, relation="leads_to", method="thread", rationale=None):
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO event_links (id, from_event_id, to_event_id, relation, confidence, rationale, method) "
                 "VALUES (:i, :f, :t, :r, 0.9, :ra, :m)"),
            {"i": str(uuid.uuid4()), "f": str(f), "t": str(t), "r": relation, "ra": rationale, "m": method},
        )


async def test_a_record_is_dated_by_its_first_report_not_by_when_prism_processed_it(world):
    async with session_scope() as s:
        eid = await world.record(s, "Captain saves the flight")
        await world.report(s, eid, SEEN - 30 * H, founder=True)  # a backlog: processed 30h after it ran
        await world.report(s, eid, SEEN - dt.timedelta(days=90))  # a live blog dated by its first post
        await world.report(s, eid, SEEN + 5.5 * H)  # an IST clock labelled UTC
    await _rebuild_projection(eid, touch=False)
    assert await _published(eid) == SEEN - 30 * H


async def test_with_no_report_inside_the_window_it_is_dated_when_first_seen(world):
    async with session_scope() as s:
        eid = await world.record(s, "Undated")
        await world.report(s, eid, SEEN - dt.timedelta(days=90), founder=True)
        await world.report(s, eid, None)
    await _rebuild_projection(eid, touch=False)
    assert await _published(eid) == SEEN


async def test_an_earlier_report_joining_moves_the_record_back_and_turns_its_links(world):
    async with session_scope() as s:
        a = await world.record(s, "Passengers subdue the attacker")
        await world.report(s, a, SEEN - 1 * H, founder=True)
        b = await world.record(s, "Captain saves the flight")
        await world.report(s, b, SEEN - 0.5 * H, founder=True)
    for eid in (a, b):
        await _rebuild_projection(eid, touch=False)
    await _link(a, b)
    await _rebuild_projection(b, touch=False)
    assert await _links(a, b) == {(a, b)}, "already the right way round: left alone"

    async with session_scope() as s:
        await world.report(s, b, SEEN - 2 * H)  # an earlier report of b arrives late
    await _rebuild_projection(b, touch=False)
    assert await _published(b) == SEEN - 2 * H
    assert await _links(a, b) == {(b, a)}, "b is now the earlier record, so it leads"


async def test_a_follow_up_link_runs_from_the_record_reported_first(world):
    """After a backlog the record founded first can hold the later report."""
    async with session_scope() as s:
        existing = await world.record(s, "Modi praises the pilot")
        await world.report(s, existing, SEEN - 1 * H, founder=True)
    await _rebuild_projection(existing, touch=False)
    async with session_scope() as s:
        new = await world.record(s, "Captain saves the flight")
        aid = await world.report(s, None, SEEN - 20 * H)
        await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                             "VALUES (:i, :e, :a, 'new_event', true)"),
                        {"i": str(uuid.uuid4()), "e": str(new), "a": str(aid)})
        await s.execute(text("INSERT INTO event_match_verdicts (article_id, event_id, noul, story_noul, model, mode) "
                             "VALUES (:a, :e, 0.1, 0.9, 'm', 'confirm')"), {"a": str(aid), "e": str(existing)})
        await _link_follow_up(s, aid, new)
    assert await _links(existing, new) == {(new, existing)}


async def test_the_thread_linker_orients_by_first_report_whatever_the_model_says(world, monkeypatch):
    async with session_scope() as s:
        event = await world.record(s, "Modi praises the pilot")
        await world.report(s, event, SEEN - 1 * H, founder=True)
        cause = await world.record(s, "Captain saves the flight")
        await world.report(s, cause, SEEN - 20 * H, founder=True)
    for eid in (event, cause):
        await _rebuild_projection(eid, touch=False)
    asked = []

    async def candidates(_eid):
        return [{"id": cause, "title": "Captain saves the flight", "summary": "s", "sector": "civic",
                 "published": SEEN - 20 * H}]

    async def chat(**kw):
        asked.append(kw["messages"])
        return ThreadLinkResult(judgements=[ThreadLinkJudgement(
            index=0, related=True, direction="event_causes_candidate", rationale="r", confidence=0.9)])

    monkeypatch.setattr(threads, "_find_candidates", candidates)
    monkeypatch.setattr(threads, "structured_chat", chat)
    monkeypatch.setattr(get_settings(), "prism_langfuse_enabled", False)
    await threads.link_event_threads(event)
    assert await _links(event, cause) == {(cause, event)}
    assert (SEEN - 1 * H).isoformat() in str(asked[0]), "the model is shown when each was first reported"


async def test_the_timeline_reads_in_order_of_first_report_and_never_shows_a_rejected_link(world):
    async with session_scope() as s:
        later = await world.record(s, "Modi praises the pilot")
        await world.report(s, later, SEEN - 1 * H, founder=True)
        first = await world.record(s, "Captain saves the flight")
        await world.report(s, first, SEEN - 20 * H, founder=True)
        rejected = await world.record(s, "An unrelated award")
        await world.report(s, rejected, SEEN - 10 * H, founder=True)
        # The extractor's day says the opposite: the order it used to give.
        for eid, day in ((later, SEEN - dt.timedelta(days=5)), (first, SEEN)):
            await s.execute(text("UPDATE events SET occurred_at = :d WHERE id = :e"), {"d": day.date(), "e": str(eid)})
    for eid in (later, first, rejected):
        await _rebuild_projection(eid, touch=False)
    await _link(first, later, rationale="the rescue drew the praise")
    await _link(first, rejected, relation="none", rationale="not one story")

    timeline = await threads.story_timeline_from_members(later, [first, later, rejected])
    devs = timeline["developments"]
    assert [d["id"] for d in devs] == [str(first), str(rejected), str(later)]
    assert devs[0]["first_published_at"] == (SEEN - 20 * H).isoformat()
    assert {d["id"]: d["why"] for d in devs} == {str(first): None, str(rejected): None,
                                                  str(later): "the rescue drew the praise"}


async def test_before_the_migration_lands_a_rebuild_names_no_new_column(monkeypatch):
    """Only the API container migrates; a worker on this code that starts first
    must not fail every attach on a column that does not exist yet."""
    sql = []

    class _Result:
        def first(self):
            return None

    class _Session:
        async def execute(self, stmt, params=None):
            sql.append(str(stmt))
            return _Result()

    monkeypatch.setattr(chronology, "_migrated", False)
    await chronology.place_in_time(_Session(), uuid.uuid4())
    assert len(sql) == 1 and "information_schema" in sql[0]


async def test_loading_a_record_never_selects_the_new_column():
    """`session.get(Event)` runs on every attach; deferred keeps the column out of it."""
    assert "first_published_at" not in str(select(Event))


async def test_the_backfill_writes_once_and_a_rerun_writes_nothing(world):
    from tools.backfill_first_published import _WRITE, plan

    async with session_scope() as s:
        eid = await world.record(s, "Backfilled")
        await world.report(s, eid, SEEN - 3 * H, founder=True)
    await plan()  # read-only, and it runs
    for expected in (1, 0):
        async with session_scope() as s:
            assert (await s.execute(_WRITE, {"ids": [str(eid)]})).rowcount == expected
    assert await _published(eid) == SEEN - 3 * H
