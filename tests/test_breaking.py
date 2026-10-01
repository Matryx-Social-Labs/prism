"""Breaking: a record many outlets report fast, in more than one language.

Calibrated 2026-10-01 on 16 days of production arrivals (first article per
outlet per record, by its own publication time, windowed as the timeline is):
>= 6 outlets within two hours of the first report and >= 2 languages fired on
18 records in the full-ingest days; the scheduled ones (match results, medals)
are "anticipated" — their story already had coverage — and are left to their
story's latest development. What remains (an actor's death, a suicide bombing,
the Pune drowning, a Supreme Court order) is about 1.6 a day.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from correlation import heat
from tests.test_verified_tier import _db_reachable

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _record(s, reports: list[tuple[str, str, int]], *, first_minutes_ago: int = 100) -> uuid.UUID:
    """A record whose first report was `first_minutes_ago`, and one article per
    (publisher, language, minutes after the first report)."""
    eid, tag = uuid.uuid4(), uuid.uuid4().hex[:8]
    t0 = datetime.now(UTC) - timedelta(minutes=first_minutes_ago)
    await s.execute(text("INSERT INTO events (id, title, sector, first_seen_at, first_published_at) "
                         "VALUES (:i, :t, 'other', :t0, :t0)"), {"i": str(eid), "t": f"Record {tag}", "t0": t0})
    for k, (publisher, lang, after) in enumerate(reports):
        sid, rid, aid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
        await s.execute(text("INSERT INTO sources (id, slug, name, source_type, publisher) VALUES (:i, :s, :s, 'rss', :p)"),
                        {"i": str(sid), "s": f"fx-{tag}-{k}", "p": f"{publisher}-{tag}"})
        await s.execute(text("INSERT INTO raw_items (id, source_id, external_id, title, raw, relevance, language, "
                             "published_at) VALUES (:i, :s, :e, 'x', '{}'::jsonb, 'relevant', :l, :p)"),
                        {"i": str(rid), "s": str(sid), "e": f"e-{tag}-{k}", "l": lang,
                         "p": t0 + timedelta(minutes=after)})
        await s.execute(text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count) "
                             "VALUES (:i, :r, 'b', 'direct', 1)"), {"i": str(aid), "r": str(rid)})
        await s.execute(text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) "
                             "VALUES (:i, :e, :a, :m, :sv)"),
                        {"i": str(uuid.uuid4()), "e": str(eid), "a": str(aid),
                         "m": "new_event" if k == 0 else "verified", "sv": k == 0})
    return eid


async def _state(s, eid):
    return (await s.execute(text("SELECT breaking_at, breaking_outlets, breaking_languages FROM events WHERE id = :e"),
                            {"e": str(eid)})).one()


SIX_TWO_LANGUAGES = [("p1", "en", 0), ("p2", "en", 10), ("p3", "hi", 20), ("p4", "en", 40), ("p5", "kn", 60),
                     ("p6", "en", 90)]


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(get_settings(), "prism_breaking", "live")


async def test_six_outlets_in_two_hours_in_two_languages_is_breaking(live):
    """2026-10-01: eight Pune school students drowned at Diveagar; 9 outlets in 5 languages within two hours."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        eid = await _record(s, SIX_TWO_LANGUAGES)
        await heat.mark_breaking(s)
        row = await _state(s, eid)
        assert row.breaking_at is not None and (row.breaking_outlets, row.breaking_languages) == (6, 3)
        await s.rollback()


async def test_five_outlets_is_not(live):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        eid = await _record(s, SIX_TWO_LANGUAGES[:5])
        await heat.mark_breaking(s)
        assert (await _state(s, eid)).breaking_at is None
        await s.rollback()


async def test_one_language_is_not(live):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        eid = await _record(s, [(p, "en", t) for p, _, t in SIX_TWO_LANGUAGES])
        await heat.mark_breaking(s)
        assert (await _state(s, eid)).breaking_at is None
        await s.rollback()


async def test_one_outlet_posting_six_times_counts_once(live):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        langs = ["en", "hi", "kn", "ta", "te", "mr"]  # one per article: a per-language count would reach six
        eid = await _record(s, [("same", lang, t) for lang, (_, _, t) in zip(langs, SIX_TWO_LANGUAGES, strict=True)])
        await heat.mark_breaking(s)
        assert (await _state(s, eid)).breaking_at is None
        await s.rollback()


async def test_reports_after_two_hours_do_not_count(live):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        late = [(p, lang, 130 + t) if k >= 4 else (p, lang, t) for k, (p, lang, t) in enumerate(SIX_TWO_LANGUAGES)]
        eid = await _record(s, late, first_minutes_ago=170)
        await heat.mark_breaking(s)
        assert (await _state(s, eid)).breaking_at is None
        await s.rollback()


async def test_an_anticipated_record_is_not_breaking(live):
    """A medal or a match result: its story was already being covered before it happened."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        eid = await _record(s, SIX_TWO_LANGUAGES)
        earlier = await _record(s, [("a1", "en", 0), ("a2", "en", 5), ("a3", "hi", 9)], first_minutes_ago=60 * 30)
        sid = uuid.uuid4()
        await s.execute(text("INSERT INTO stories (id, slug, label, \"cast\", member_event_ids, status, anchor_event_id) "
                             "VALUES (:i, :s, 'x', '[]'::jsonb, '[]'::jsonb, 'shadow', :a)"),
                        {"i": str(sid), "s": f"fx-{sid.hex[:12]}", "a": str(earlier)})
        for e in (earlier, eid):
            await s.execute(text("INSERT INTO story_events (event_id, story_id, facet) VALUES (:e, :s, 'event')"),
                            {"e": str(e), "s": str(sid)})
        await heat.mark_breaking(s)
        assert (await _state(s, eid)).breaking_at is None
        await s.rollback()


async def test_an_old_record_is_never_marked(live):
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        eid = await _record(s, SIX_TWO_LANGUAGES, first_minutes_ago=60 * 5)
        await heat.mark_breaking(s)
        assert (await _state(s, eid)).breaking_at is None
        await s.rollback()


async def test_off_marks_nothing(monkeypatch):
    if not await _db_reachable():
        pytest.skip("no database")
    monkeypatch.setattr(get_settings(), "prism_breaking", "off")
    async with session_scope() as s:
        eid = await _record(s, SIX_TWO_LANGUAGES)
        await heat.mark_breaking(s)
        assert (await _state(s, eid)).breaking_at is None
        await s.rollback()
