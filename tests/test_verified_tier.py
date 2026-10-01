"""The verified matching tier: gist candidates, one Jev call, attach only on its word.

Jev is mocked; what is under test is the tier's contract — who gets asked, what
an answer does in each mode, and that every failure leaves the article to found
its own event, exactly as before the tier existed.
"""

import math
import random
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import correlation.clustering as clustering
import correlation.verify as verify
from common.config import get_settings
from common.db import session_scope
from common.decisions import Decisions, NoulAnswer

pytestmark = pytest.mark.asyncio(loop_scope="session")

FLOOR = clustering._scale()["gist_candidate"]


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def _direction() -> list[float]:
    """A random unit vector: the shared local database holds other sessions'
    gists, and a fixed one would find them."""
    v = [random.gauss(0, 1) for _ in range(768)]
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def _at(base: list[float], distance: float) -> list[float]:
    """A unit vector exactly `distance` (cosine) from `base`."""
    other = _direction()
    dot = sum(a * b for a, b in zip(base, other, strict=True))
    perp = [o - dot * b for o, b in zip(other, base, strict=True)]
    n = math.sqrt(sum(x * x for x in perp))
    c = 1.0 - distance
    return [c * b + math.sqrt(1 - c * c) * p / n for b, p in zip(base, perp, strict=True)]


def _vec(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.7f}" for x in v) + "]"


async def _event_with_member(s, title: str, gist: list[float]) -> uuid.UUID:
    eid, sid, rid, aid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    tag = uuid.uuid4().hex[:8]
    await s.execute(text("INSERT INTO events (id, title, summary, sector) VALUES (:i, :t, 'founder summary', 'civic')"),
                    {"i": str(eid), "t": title})
    await s.execute(text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
                    {"i": str(sid), "s": f"fixture-{tag}"})
    await s.execute(text("INSERT INTO raw_items (id,source_id,external_id,title,raw,relevance) "
                         "VALUES (:i,:s,:e,'fixture','{}'::jsonb,'relevant')"),
                    {"i": str(rid), "s": str(sid), "e": f"ext-{tag}"})
    await s.execute(text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count,gist_embedding) "
                         "VALUES (:i,:r,'body','direct',1,CAST(:g AS vector))"),
                    {"i": str(aid), "r": str(rid), "g": _vec(gist)})
    await s.execute(text("INSERT INTO event_memberships (id,event_id,article_id,match_type,is_survivor) "
                         "VALUES (:i,:e,:a,'new_event',true)"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "a": str(aid)})
    return eid


async def _incoming_article(s) -> uuid.UUID:
    sid, rid, aid = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    tag = uuid.uuid4().hex[:8]
    await s.execute(text("INSERT INTO sources (id,slug,name,source_type) VALUES (:i,:s,:s,'rss')"),
                    {"i": str(sid), "s": f"fixture-{tag}"})
    await s.execute(text("INSERT INTO raw_items (id,source_id,external_id,title,raw,relevance) "
                         "VALUES (:i,:s,:e,'incoming','{}'::jsonb,'relevant')"),
                    {"i": str(rid), "s": str(sid), "e": f"ext-{tag}"})
    await s.execute(text("INSERT INTO articles (id,raw_item_id,clean_text,retrieval_tier,word_count) "
                         "VALUES (:i,:r,'body','direct',1)"), {"i": str(aid), "r": str(rid)})
    return aid


@pytest.fixture
def jev(monkeypatch):
    """Answers every question with the noul given per event title; records calls."""
    calls: list[dict] = []
    answers: dict[str, float] = {}

    async def fake_decide(state, questions, **_):
        calls.append(state)
        out = {}
        for k in questions:
            block = state[f"EVENT_{k.split('_')[1]}"]
            title = block.split("Headline: ")[1].split("\n")[0]
            out[k] = NoulAnswer(noul=answers.get(title, 0.0))
        return Decisions(answers=out, model="typesafe/jev-test")

    monkeypatch.setattr(verify, "decide", fake_decide)
    return calls, answers


async def _run(s, gist, article_id):
    return await clustering._match_by_gist_verified(s, gist, "Published now by x.\nHeadline: h\nSummary: s", None, article_id)


async def test_live_attaches_to_the_event_jev_confirms(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, answers = jev
    monkeypatch.setattr(get_settings(), "prism_event_verify", "live")
    g = _direction()
    tag = uuid.uuid4().hex[:6]
    async with session_scope() as s:
        same = await _event_with_member(s, f"Actor dies at 56 {tag}", _at(g, FLOOR / 2))
        await _event_with_member(s, f"Actor's films remembered {tag}", _at(g, FLOOR / 3))
        answers[f"Actor dies at 56 {tag}"] = 0.94
        aid = await _incoming_article(s)
        match = await _run(s, g, aid)
        assert match is not None and match.event_id == same and match.match_type == "verified"
        assert len(calls) == 1, "one Jev call per article, every candidate in it"
        stored = (await s.execute(text("SELECT count(*) FROM event_match_verdicts WHERE article_id = :a"),
                                  {"a": str(aid)})).scalar_one()
        assert stored == 2, "every answer is recorded, the refused one too"
        await s.rollback()


async def test_a_templated_lookalike_jev_refuses_founds_its_own_event(monkeypatch, jev):
    """Two cooperative societies' annual results sit at gist cosine ~0.95 — the
    case no threshold separates. Jev's 'no' must leave the article on its own."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    monkeypatch.setattr(get_settings(), "prism_event_verify", "live")
    g = _direction()
    tag = uuid.uuid4().hex[:6]
    async with session_scope() as s:
        await _event_with_member(s, f"Maruti Society earns 2.74 crore profit {tag}", _at(g, FLOOR / 2))
        answers[f"Maruti Society earns 2.74 crore profit {tag}"] = 0.12
        aid = await _incoming_article(s)
        assert await _run(s, g, aid) is None
        await s.rollback()


async def test_shadow_asks_and_records_but_never_attaches(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, answers = jev
    monkeypatch.setattr(get_settings(), "prism_event_verify", "shadow")
    g = _direction()
    tag = uuid.uuid4().hex[:6]
    async with session_scope() as s:
        await _event_with_member(s, f"Bus fire kills nine {tag}", _at(g, FLOOR / 2))
        answers[f"Bus fire kills nine {tag}"] = 0.97
        aid = await _incoming_article(s)
        assert await _run(s, g, aid) is None, "shadow attached an article"
        assert len(calls) == 1
        mode = (await s.execute(text("SELECT mode FROM event_match_verdicts WHERE article_id = :a"),
                                {"a": str(aid)})).scalar_one()
        assert mode == "shadow"
        await s.rollback()


async def test_off_asks_nobody(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, _ = jev
    monkeypatch.setattr(get_settings(), "prism_event_verify", "off")
    g = _direction()
    async with session_scope() as s:
        await _event_with_member(s, "anything", _at(g, FLOOR / 2))
        aid = await _incoming_article(s)
        assert await _run(s, g, aid) is None
        assert calls == []
        await s.rollback()


async def test_nothing_within_the_floor_asks_nobody(monkeypatch, jev):
    if not await _db_reachable():
        pytest.skip("no database")
    calls, _ = jev
    monkeypatch.setattr(get_settings(), "prism_event_verify", "live")
    g = _direction()
    async with session_scope() as s:
        await _event_with_member(s, "far away", _at(g, FLOOR * 3))
        aid = await _incoming_article(s)
        assert await _run(s, g, aid) is None
        assert calls == [], "Jev was paid for a candidate the gist had already ruled out"
        await s.rollback()


async def test_a_failed_or_slow_judge_founds_a_new_event(monkeypatch, jev):
    """Jev runs under correlation's lock: an outage or a quota pause must cost a
    missed merge, never a stalled pipeline or a crash."""
    if not await _db_reachable():
        pytest.skip("no database")
    monkeypatch.setattr(get_settings(), "prism_event_verify", "live")
    monkeypatch.setattr(verify, "VERIFY_TIMEOUT_S", 0.05)

    async def hangs(*_a, **_k):
        import asyncio
        await asyncio.sleep(5)

    monkeypatch.setattr(verify, "decide", hangs)
    g = _direction()
    async with session_scope() as s:
        await _event_with_member(s, "slow", _at(g, FLOOR / 2))
        aid = await _incoming_article(s)
        import time
        started = time.monotonic()
        assert await _run(s, g, aid) is None
        assert time.monotonic() - started < 1.0, "the judge held correlation's lock past its ceiling"
        await s.rollback()


def test_the_gist_is_the_english_headline_and_summary():
    shared = {"headline": "Bollywood actor Mushtaq Khan dies at 56",
              "headline_summary": "The actor died in Mumbai after a battle with cancer."}
    assert verify.gist_text(shared, "नहीं रहे मुश्ताक खान") == (
        "Bollywood actor Mushtaq Khan dies at 56. The actor died in Mumbai after a battle with cancer.")
    # No English headline: the outlet's title carries the summary.
    assert verify.gist_text({"headline_summary": "S."}, "Raw title").startswith("Raw title. S.")
    # No summary: no gist — a title alone is not what was measured.
    assert verify.gist_text({"headline": "H"}, "Raw") is None


async def test_a_database_failure_is_never_swallowed_as_no_match(monkeypatch, jev):
    """REGRESSION: the verdict INSERT sat inside the try that turns a Jev failure
    into "no match". A database error there was swallowed with the transaction
    already aborted, so the attach that followed failed and the message looped.
    Only the network call may fall back; database errors propagate."""
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    monkeypatch.setattr(get_settings(), "prism_event_verify", "live")

    async def broken(*_a, **_k):
        raise RuntimeError("verdict insert failed")

    monkeypatch.setattr(clustering, "record", broken)
    g = _direction()
    tag = uuid.uuid4().hex[:6]
    async with session_scope() as s:
        await _event_with_member(s, f"Seema Kumari wins bronze {tag}", _at(g, FLOOR / 2))
        answers[f"Seema Kumari wins bronze {tag}"] = 0.95
        aid = await _incoming_article(s)
        with pytest.raises(RuntimeError, match="verdict insert failed"):
            await _run(s, g, aid)
        await s.rollback()


async def test_out_of_window_lookalikes_never_crowd_out_an_in_window_candidate(monkeypatch, jev):
    """The gist search is an index scan for the nearest articles (2026-10-01: the
    seq scan took 1.02 s per article under the match lock). The 14-day window is
    applied INSIDE that scan (pgvector iterative scan), so older articles nearer
    the gist cannot fill the scan's quota and hide the record that is in window."""
    if not await _db_reachable():
        pytest.skip("no database")
    calls, answers = jev
    monkeypatch.setattr(get_settings(), "prism_event_verify", "live")
    monkeypatch.setattr(clustering, "GIST_ANN", 2)
    g, tag = _direction(), uuid.uuid4().hex[:8]
    async with session_scope() as s:
        for k in range(3):  # nearer, but reported a month ago
            old = await _event_with_member(s, f"Old lookalike {k} {tag}", _at(g, FLOOR / 8))
            await s.execute(text("UPDATE events SET last_updated_at = now() - interval '30 days' WHERE id = :e"),
                            {"e": str(old)})
            await s.execute(text("UPDATE articles SET created_at = now() - interval '30 days' WHERE id IN "
                                 "(SELECT article_id FROM event_memberships WHERE event_id = :e)"), {"e": str(old)})
        fresh = await _event_with_member(s, f"In window {tag}", _at(g, FLOOR / 2))
        answers[f"In window {tag}"] = 0.95
        aid = await _incoming_article(s)
        from datetime import UTC, datetime
        match = await clustering._match_by_gist_verified(s, g, "Published now by x.\nHeadline: h\nSummary: s",
                                                         datetime.now(UTC), aid)
        assert match is not None and match.event_id == fresh
        await s.rollback()
