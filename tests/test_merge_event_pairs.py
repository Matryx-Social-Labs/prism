"""Merging duplicate RECORDS, judged record to record (tools/merge_duplicates --events).

The shadow-verdict backlog only reaches a copy whose every article Jev judged.
Duplicate records built from several articles each (the Parvesh Verma slap was
six records of 7, 4, 3, 2, 1… outlets) need the records themselves judged: each
record's founding headline + summary against another's, candidates by the
founders' gists. Groups are STARS: a record joins a survivor only on its own
verdict against that survivor, never through a third record.

Jev is mocked. The shared local database holds other tests' records, so every
database test filters the plan down to the records it made.
"""

import math
import random
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import correlation.verify as verify
from api.main import app
from common.db import session_scope
from common.decisions import Decisions, NoulAnswer
from correlation import merge
from correlation.consumer import _rebuild_projection

T0 = datetime(2026, 9, 27, 10, tzinfo=UTC)


def _rec(publishers: int, hours: float = 0) -> merge.Record:
    return merge.Record(id=uuid.uuid4(), founder=uuid.uuid4(), publishers=publishers,
                        first_seen=T0 + timedelta(hours=hours))


def _k(a: merge.Record, b: merge.Record) -> frozenset:
    return frozenset((a.id, b.id))


def _folds(merges) -> set[tuple]:
    return {(m.absorbed, m.survivor) for m in merges}


# ── The grouping rule, no database ──────────────────────────────────────────


def test_a_record_reached_only_through_another_joins_only_on_its_own_verdict_against_the_survivor():
    """A~B and B~C say nothing about A~C: C is asked against A directly, and
    joins A only if Jev says so. It never joins B, which is not a survivor."""
    a, b, c = _rec(5), _rec(3, 1), _rec(1, 2)
    recs = {r.id: r for r in (a, b, c)}
    chain = {_k(a, b): 0.95, _k(b, c): 0.95}

    merges, wanted = merge.stars(recs, chain)
    assert _folds(merges) == {(b.id, a.id)}
    assert wanted == {_k(c, a)}  # the one extra call

    merges, wanted = merge.stars(recs, {**chain, _k(a, c): 0.30})
    assert _folds(merges) == {(b.id, a.id)} and wanted == set()

    merges, wanted = merge.stars(recs, {**chain, _k(a, c): 0.90})
    assert {(m.absorbed, m.survivor, m.noul) for m in merges} == {(b.id, a.id, 0.95), (c.id, a.id, 0.90)}
    assert all(m.whole for m in merges) and wanted == set()


def test_records_first_seen_further_apart_than_the_window_never_merge():
    a, late = _rec(5), _rec(1, 73)
    assert merge.stars({r.id: r for r in (a, late)}, {_k(a, late): 0.99}) == ([], set())

    # Nor through a record in between: B is 40h from both, C is 80h from A.
    a, b, c = _rec(5), _rec(3, 40), _rec(1, 80)
    merges, wanted = merge.stars({r.id: r for r in (a, b, c)}, {_k(a, b): 0.95, _k(b, c): 0.95, _k(a, c): 0.99})
    assert _folds(merges) == {(b.id, a.id)} and wanted == set()


def test_the_survivor_is_the_record_with_the_most_publishers_then_the_earliest():
    first_but_small = _rec(2, 0)
    big_later = _rec(5, 3)
    big_earlier = _rec(5, 1)
    recs = {r.id: r for r in (first_but_small, big_later, big_earlier)}
    every_pair = {_k(x, y): 0.95 for x in recs.values() for y in recs.values() if x.id != y.id}
    merges, _ = merge.stars(recs, every_pair)
    assert _folds(merges) == {(first_but_small.id, big_earlier.id), (big_later.id, big_earlier.id)}


def test_below_the_floor_is_not_a_merge():
    a, b = _rec(5), _rec(1, 1)
    assert merge.stars({r.id: r for r in (a, b)}, {_k(a, b): 0.84}) == ([], set())


# ── Through the database, Jev mocked ───────────────────────────────────────


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def _direction() -> list[float]:
    """A random unit vector: the shared database holds other tests' gists."""
    v = [random.gauss(0, 1) for _ in range(768)]
    n = math.sqrt(sum(x * x for x in v))
    return [x / n for x in v]


def _at(base: list[float], distance: float) -> list[float]:
    """A unit vector `distance` (cosine) from `base`, in a random direction."""
    other = _direction()
    dot = sum(a * b for a, b in zip(base, other, strict=True))
    perp = [o - dot * b for o, b in zip(other, base, strict=True)]
    n = math.sqrt(sum(x * x for x in perp))
    c = 1.0 - distance
    return [c * b + math.sqrt(1 - c * c) * p / n for b, p in zip(base, perp, strict=True)]


async def _article(s, event_id: uuid.UUID, match_type: str, gist: list[float] | None = None) -> uuid.UUID:
    """One article from its own outlet, as the consumer files it."""
    src, raw, art = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    await s.execute(text("INSERT INTO sources (id, slug, name, source_type) VALUES (:i, :s, :s, 'rss')"),
                    {"i": str(src), "s": f"ev-{src.hex[:10]}"})
    await s.execute(
        text("INSERT INTO raw_items (id, source_id, external_id, url, title, raw, relevance, published_at) "
             "VALUES (:i, :s, :x, :u, 'report', '{}'::jsonb, 'relevant', now() - interval '1 hour')"),
        {"i": str(raw), "s": str(src), "x": raw.hex, "u": f"https://x.example/{raw}"},
    )
    await s.execute(
        text("INSERT INTO articles (id, raw_item_id, clean_text, retrieval_tier, word_count, gist_embedding) "
             "VALUES (:i, :r, 'x', 'rss', 1, CAST(:g AS vector))"),
        {"i": str(art), "r": str(raw), "g": "[" + ",".join(f"{x:.7f}" for x in gist) + "]" if gist else None},
    )
    await s.execute(text("INSERT INTO enrichments (id, article_id, summary, event_type) VALUES (:i, :a, 's', 'report')"),
                    {"i": str(uuid.uuid4()), "a": str(art)})
    await s.execute(
        text("INSERT INTO event_memberships (id, event_id, article_id, match_type, is_survivor) VALUES (:i, :e, :a, :t, :f)"),
        {"i": str(uuid.uuid4()), "e": str(event_id), "a": str(art), "t": match_type, "f": match_type == "new_event"},
    )
    return art


async def _record(title: str, gist: list[float], *, publishers: int = 1, minutes_ago: int = 120) -> uuid.UUID:
    """A served record: its founder carries the gist; every other member joined
    on shared actors — which the shadow-verdict backlog could never move."""
    eid = uuid.uuid4()
    async with session_scope() as s:
        await s.execute(
            text("INSERT INTO events (id, title, headline_by, summary, sector, subject_path, regions, first_seen_at, last_updated_at) "
                 "VALUES (:i, :t, 'prism', :t, 'politics', 'politics', ARRAY['IN'], now() - make_interval(mins => :m), now())"),
            {"i": str(eid), "t": title, "m": minutes_ago},
        )
        await _article(s, eid, "new_event", gist)
        for _ in range(publishers - 1):
            await _article(s, eid, "entity_overlap")
    await _rebuild_projection(eid)
    return eid


@pytest.fixture
def jev(monkeypatch):
    """Answers per unordered pair of headlines; records every pair asked."""
    asked: list[frozenset] = []
    answers: dict[frozenset, float] = {}

    def headline(block: str) -> str:
        return block.split("Headline: ")[1].split("\n")[0]

    async def fake_decide(state, questions, **_):
        out = {}
        for k in questions:
            pair = frozenset((headline(state["ARTICLE"]), headline(state[f"EVENT_{k.split('_')[1]}"])))
            asked.append(pair)
            out[k] = NoulAnswer(noul=answers.get(pair, 0.0))
        return Decisions(answers=out, model="typesafe/jev-test")

    monkeypatch.setattr(verify, "decide", fake_decide)
    return asked, answers


def _mine(p: merge.PairPlan, *ids: uuid.UUID) -> dict:
    return {m.absorbed: m for m in p.merges if m.absorbed in ids}


async def _scalar(sql: str, **params):
    async with session_scope() as s:
        return (await s.execute(text(sql), {k: str(v) for k, v in params.items()})).scalar()


@pytest.mark.asyncio(loop_scope="session")
async def test_duplicate_records_are_judged_record_to_record_and_folded_into_one(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    asked, answers = jev
    tag = uuid.uuid4().hex[:8]
    base = _direction()
    b_gist = _at(base, 0.06)
    s = await _record(f"S {tag}", base, publishers=3)
    b = await _record(f"B {tag}", b_gist, publishers=2, minutes_ago=90)
    # 0.06 from B, so ~0.12 from S: a gist candidate of B's only.
    c = await _record(f"C {tag}", _at(b_gist, 0.06), minutes_ago=60)
    answers.update({frozenset((f"S {tag}", f"B {tag}")): 0.95, frozenset((f"B {tag}", f"C {tag}")): 0.95,
                    frozenset((f"S {tag}", f"C {tag}")): 0.92})

    plan = await merge.plan_events(days=1)
    mine = _mine(plan, b, c)
    assert {k: m.survivor for k, m in mine.items()} == {b: s, c: s}
    # C was reached through B, so it was asked about S itself — one extra call.
    assert frozenset((f"S {tag}", f"C {tag}")) in asked
    # A dry run writes nothing.
    assert await _scalar("SELECT count(*) FROM event_match_verdicts WHERE event_id IN (:s, :b, :c)", s=s, b=b, c=c) == 0

    # Recorded, the verdicts are the plan: a re-run asks nothing again.
    await merge.record_pairs(plan.judged)
    assert await _scalar("SELECT count(*) FROM event_match_verdicts WHERE event_id IN (:s, :b, :c) AND mode = 'pair'",
                         s=s, b=b, c=c) == 3
    asked.clear()
    again = await merge.plan_events(days=1)
    assert {k: m.survivor for k, m in _mine(again, b, c).items()} == {b: s, c: s}
    assert not [p for p in asked if any(tag in t for t in p)]

    # B holds an article nobody judged; judged as a record, it moves whole.
    for m in mine.values():
        assert await merge.apply(m) is True
    assert await _scalar("SELECT count(*) FROM events WHERE id IN (:b, :c) AND merged_into = :s", b=b, c=c, s=s) == 2
    assert await _scalar("SELECT count(*) FROM event_memberships WHERE event_id = :s", s=s) == 6
    assert await _scalar("SELECT projection->>'source_count' FROM events WHERE id = :s", s=s) == "6"

    # Idempotent: merged records leave the plan, and a second apply does nothing.
    assert _mine(await merge.plan_events(days=1), b, c) == {}
    for m in mine.values():
        assert await merge.apply(m) is False


@pytest.mark.asyncio(loop_scope="session")
async def test_a_record_folded_by_its_own_verdict_leaves_every_list_and_redirects(jev):
    if not await _db_reachable():
        pytest.skip("no database")
    _, answers = jev
    tag = uuid.uuid4().hex[:8]
    base = _direction()
    s = await _record(f"Zqxv{tag} survivor", base, publishers=2)
    b = await _record(f"Zqxv{tag} copy", _at(base, 0.04), publishers=2, minutes_ago=90)
    answers[frozenset((f"Zqxv{tag} survivor", f"Zqxv{tag} copy"))] = 0.9

    async def listed(ac) -> dict[str, set[str]]:
        async def ids(url, key="items", **params):
            return {str(r.get("id")) for r in (await ac.get(url, params=params)).json()[key]}
        return {"feed": await ids("/api/v1/feed", sector="politics", limit=100),
                "search": await ids("/api/v1/search", q=f"Zqxv{tag}")}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        before = await listed(ac)
    assert all(str(b) in got for got in before.values()), before

    plan = await merge.plan_events(days=1)
    assert await merge.apply(_mine(plan, b)[b])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
        after = await listed(ac)
        assert {k for k, got in after.items() if str(b) in got} == set()
        r = await ac.get(f"/api/v1/events/{b}")
        assert r.status_code == 308
        assert r.headers["location"] == f"/api/v1/events/{s}"
