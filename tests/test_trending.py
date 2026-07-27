"""Trending stories: the overlap primitive, reconciliation idempotency, and the
serving contract (scoping + the merge redirect that keeps shared links stable)."""

import uuid
from datetime import UTC, datetime

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common.db import session_scope
from correlation.trending import (
    _cast_jaccard,
    _converge_existing,
    _overlap,
    _same_story,
    reconcile_stories,
)

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


def test_overlap_ratio():
    # |A∩B| / min(|A|,|B|) — the "same story" test.
    assert _overlap({"1", "2", "3"}, {"2", "3", "4"}) == pytest.approx(2 / 3)  # ≥0.6 → same
    assert _overlap({"1", "2"}, {"3", "4"}) == 0.0  # disjoint → different
    assert _overlap({"1", "2", "3"}, {"1"}) == 1.0  # subset → same
    assert _overlap(set(), {"1"}) == 0.0  # empty guard


def test_cast_identity_dedup():
    # story_timeline's 30-event cap gives divergent member subsets of one big cluster
    # per seed, so member-overlap alone splits it. Cast (stable protagonists) fixes it.
    cjp_a = ["Cockroach Janta Party", "Pradhan", "Delhi Police", "Modi"]
    cjp_b = ["Pradhan", "Cockroach Janta Party", "Delhi Police", "Wangchuk"]
    assert _cast_jaccard(cjp_a, cjp_b) >= 0.5  # 3 shared / 5 union
    # members barely overlap (0.33 < 0.6) but cast marks them the SAME story.
    assert _same_story({"1", "2", "3"}, cjp_a, {"3", "4", "5"}, cjp_b)
    # a genuinely different story: disjoint cast + members → NOT merged.
    assert not _same_story({"1", "2"}, cjp_a, {"9", "8"}, ["Donald Trump", "Marco Rubio"])


def test_same_story_idf_magnet_aware():
    """IDF-weighted shared cast re-merges a Leiden over-split (two communities sharing
    SPECIFIC actors) but refuses to re-merge veto-separated stories that share only
    national MAGNETS — the failure mode an absolute shared-cast count had."""
    df = {
        "Cockroach Janta Party": 8.0, "Delhi Police": 15.0,
        "Narendra Modi": 200.0, "Indian National Congress": 150.0, "Bharatiya Janata Party": 180.0,
    }
    # Genuine over-split: disjoint members, but share the specific CJP + Delhi Police.
    a = ["Cockroach Janta Party", "Delhi Police", "Narendra Modi", "X", "Y"]
    b = ["Cockroach Janta Party", "Delhi Police", "Narendra Modi", "P", "Q"]
    assert _same_story({"1"}, a, {"2"}, b, df)  # merged via specific actors (IDF)
    # Veto-separated: share exactly 3 MAGNETS, distinct otherwise (cast Jaccard 3/13<0.5).
    cjp = ["Narendra Modi", "Indian National Congress", "Bharatiya Janata Party",
           "Cockroach Janta Party", "Delhi Police", "A", "B", "C"]
    neet = ["Narendra Modi", "Indian National Congress", "Bharatiya Janata Party",
            "D", "E", "F", "G", "H"]
    assert not _same_story({"1"}, cjp, {"2"}, neet, df)  # magnets don't clear the IDF floor


async def test_converge_existing_collapses_duplicate_stories():
    """The self-healing pass: active stories that are the same story as each other
    (not just vs a fresh community) must collapse into the oldest, and genuinely
    distinct stories must survive. Grounded in the real prod bug — one CJP story
    fragmented into cards whose FULL casts share only 3 of 8 members (Jaccard
    0.23–0.45, under CAST_SAME_STORY) but whose SPECIFIC protagonists (Cockroach Janta
    Party, Delhi Police) match. IDF-weighted shared cast re-merges them; a story that
    shares only national MAGNETS (Modi/BJP/Congress) must NOT merge (veto separation)."""

    class _StubSession:
        def __init__(self):
            self.merged = []

        async def execute(self, _clause, params=None):
            if params and "into" in params:
                self.merged.append((params["sid"], params["into"]))

    def ts(minute):
        return datetime(2026, 7, 23, 14, minute, tzinfo=UTC)

    # IDF weights: CJP-specific actors are rare (low df), national magnets are ubiquitous.
    df = {
        "Cockroach Janta Party": 8.0, "Dharmendra Pradhan": 12.0, "Delhi Police": 15.0,
        "Sonam Wangchuk": 10.0, "Rahul Gandhi": 80.0, "Akhilesh Yadav": 50.0,
        "C. Joseph Vijay": 20.0, "Tamilaga Vettri Kazhagam": 18.0,
        "Narendra Modi": 200.0, "Bharatiya Janata Party": 180.0, "Indian National Congress": 150.0,
        "Amit Shah": 90.0, "Lok Sabha": 100.0,
    }

    # The four cards' actual casts, most-covered-first. Pairwise cast Jaccard is
    # 0.23–0.45 (secondary actors diverge per BFS window) — only the dominant
    # {Cockroach Janta Party, Dharmendra Pradhan} survives across all of them.
    stories = {
        "old": {"members": {"1", "2"}, "first": ts(3),  # oldest → the survivor
                "cast": ["Dharmendra Pradhan", "Delhi Police", "Cockroach Janta Party", "Sonam Wangchuk",
                         "Rahul Gandhi", "Narendra Modi", "Bharatiya Janata Party", "Akhilesh Yadav"]},
        "vijay": {"members": {"3", "4"}, "first": ts(12),
                  "cast": ["Dharmendra Pradhan", "C. Joseph Vijay", "Cockroach Janta Party", "Tamilaga Vettri Kazhagam",
                           "Delhi Police", "Sonam Wangchuk", "DMK", "Narendra Modi"]},
        "modi": {"members": {"5", "6"}, "first": ts(12),
                 "cast": ["Narendra Modi", "Dharmendra Pradhan", "Cockroach Janta Party", "Lok Sabha",
                          "Amit Shah", "Akhilesh Yadav", "Delhi Police", "Indian National Congress"]},
        "wangchuk": {"members": {"7"}, "first": ts(12),
                     "cast": ["Cockroach Janta Party", "Sonam Wangchuk", "Dharmendra Pradhan", "Delhi Police",
                              "Rahul Gandhi", "JP Nadda", "Saurav Das", "Medanta Hospital"]},
        # shares only Pradhan (1 of top-3) with CJP — an unrelated education story → stays
        "edu": {"members": {"80"}, "first": ts(12), "cast": ["Dharmendra Pradhan", "NCERT", "CBSE"]},
        # wholly unrelated → stays
        "trump": {"members": {"77"}, "first": ts(3), "cast": ["Donald Trump", "Marco Rubio", "White House"]},
        # shares only NATIONAL MAGNETS (Modi/BJP/Congress/Amit Shah) with the CJP cards —
        # the old absolute-count merge would wrongly fold it in; IDF must keep it separate.
        "neet": {"members": {"90"}, "first": ts(12),
                 "cast": ["Narendra Modi", "Bharatiya Janata Party", "Indian National Congress", "Amit Shah"]},
    }
    session = _StubSession()
    await _converge_existing(session, stories, df)

    # CJP dupes merged (shared SPECIFIC cast); distinct + magnet-only stories survive.
    assert set(stories) == {"old", "edu", "trump", "neet"}
    assert all(into == "old" for _, into in session.merged)  # oldest is the canonical survivor
    assert {sid for sid, _ in session.merged} == {"vijay", "modi", "wangchuk"}


async def test_reconcile_is_idempotent():
    """Two passes over the same data must not duplicate stories (the match-and-update
    path). Verifies the core state machine converges."""
    if not await _db_reachable():
        pytest.skip("no database")
    async with session_scope() as s:
        n1 = await reconcile_stories(s)
    async with session_scope() as s:
        before = (await s.execute(text("SELECT count(*) FROM stories WHERE merged_into IS NULL"))).scalar_one()
        n2 = await reconcile_stories(s)
    async with session_scope() as s:
        after = (await s.execute(text("SELECT count(*) FROM stories WHERE merged_into IS NULL"))).scalar_one()
    assert n1 == n2  # same active count
    assert before == after  # no new stories created on the second pass


async def test_serving_scope_and_merge_redirect():
    """List scoping + the merge redirect (a merged story's slug resolves to the
    canonical one, so an old share link never breaks)."""
    if not await _db_reachable():
        pytest.skip("no database")
    tag = uuid.uuid4().hex[:8]
    canonical, merged = uuid.uuid4(), uuid.uuid4()
    a_slug, b_slug = f"active-{tag}", f"merged-{tag}"
    try:
        async with session_scope() as s:
            await s.execute(
                text(
                    'INSERT INTO stories (id,slug,label,"cast",member_event_ids,regions,source_count,velocity,status) '
                    "VALUES (:i,:sl,:lb,'[\"A\"]'::jsonb,'[]'::jsonb,ARRAY['IN-KA'],5,3,'active')"
                ),
                {"i": str(canonical), "sl": a_slug, "lb": "Active story"},
            )
            await s.execute(
                text(
                    'INSERT INTO stories (id,slug,label,"cast",member_event_ids,source_count,velocity,status,merged_into) '
                    "VALUES (:i,:sl,'Merged','[]'::jsonb,'[]'::jsonb,4,2,'dormant',:into)"
                ),
                {"i": str(merged), "sl": b_slug, "into": str(canonical)},
            )
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as ac:
            slugs = {x["slug"] for x in (await ac.get("/api/v1/trending?limit=50")).json()["stories"]}
            assert a_slug in slugs and b_slug not in slugs  # merged/dormant excluded from the list

            ka = {x["slug"] for x in (await ac.get("/api/v1/trending?state=IN-KA")).json()["stories"]}
            tn = {x["slug"] for x in (await ac.get("/api/v1/trending?state=IN-TN")).json()["stories"]}
            assert a_slug in ka and a_slug not in tn  # geo scope filters

            # A shared link to the MERGED story resolves to the canonical one.
            d = (await ac.get(f"/api/v1/trending/{b_slug}")).json()
            assert d["canonical_slug"] == a_slug

            assert (await ac.get(f"/api/v1/trending/no-such-{tag}")).status_code == 404
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM stories WHERE id = ANY(:ids)"), {"ids": [str(canonical), str(merged)]})


async def test_two_communities_of_one_story_fold_instead_of_minting_duplicates(monkeypatch):
    """REGRESSION: trending fragmented without bound — a merge/re-create treadmill.

    Leiden routinely splits one real story into several communities (a protest and
    its offshoots). The matching loop claimed a story for the first community; the
    rest then found `matches` empty — the only story they matched was already
    claimed — and CREATED duplicates. `_converge_existing` collapsed those on the
    next pass, and this loop minted them again from the same communities, forever.

    Observed in production over 90 minutes: one protest grew from 4 to 7 of 17
    trending slots, with 6 pairs that `_same_story` already called identical and
    two slugs differing only in the trailing hash.
    """
    created: list[dict] = []
    updated: list[tuple[str, list[str]]] = []

    cast = ["Cockroach Janta Party", "Dharmendra Pradhan", "Delhi Police"]
    # Two slices of ONE story: disjoint members, same protagonists. That is exactly
    # the shape cast-identity matching exists to re-join.
    communities = [
        {"member_ids": ["1", "2"], "cast": cast, "hero_title": "a", "hero_event_id": None,
         "sector": "politics", "regions": ["IN"], "total_sources": 9, "recent_sources": 4},
        {"member_ids": ["3", "4"], "cast": cast, "hero_title": "b", "hero_event_id": None,
         "sector": "politics", "regions": ["IN"], "total_sources": 7, "recent_sources": 3},
    ]

    class _Stub:
        async def execute(self, _clause, params=None):
            class _R:
                def mappings(self):
                    return self
                def all(self):
                    # One existing story that both communities match.
                    return [{"id": "S", "member_event_ids": ["1", "2"], "cast": cast,
                             "first_seen_at": datetime(2026, 7, 23, 14, 0, tzinfo=UTC)}]
                def scalar(self):
                    return None
            return _R()

    import correlation.trending as T
    monkeypatch.setattr(T, "detect_trending_communities", lambda _s: _aw(communities))
    monkeypatch.setattr(T, "_cast_df", lambda _s, _n: _aw({}))
    monkeypatch.setattr(T, "_converge_existing", lambda *_a: _aw(None))
    monkeypatch.setattr(T, "_community_facts", lambda _s, ids: _aw(
        {"cast": cast, "hero_title": "a", "hero_event_id": None, "sector": "politics",
         "regions": ["IN"], "total_sources": 16, "recent_sources": 7}))

    async def fake_create(_s, c):
        created.append(c)
        return "NEW"

    async def fake_update(_s, sid, c):
        updated.append((sid, list(c["member_ids"])))

    monkeypatch.setattr(T, "_create_story", fake_create)
    monkeypatch.setattr(T, "_update_story", fake_update)

    await T.reconcile_stories(_Stub())

    assert created == [], f"minted {len(created)} duplicate story/ies for one real story"
    assert [sid for sid, _ in updated] == ["S", "S"], "both slices must land on the same story"
    # And the fold keeps every member, rather than the second slice overwriting the first.
    assert set(updated[-1][1]) == {"1", "2", "3", "4"}


def _aw(value):
    """Wrap a plain value in an awaitable, for monkeypatching async collaborators."""
    async def _inner(*_a, **_k):
        return value
    return _inner()
