"""Trending stories: the overlap primitive, reconciliation idempotency, and the
serving contract (scoping + the merge redirect that keeps shared links stable)."""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from common.db import session_scope
from correlation.trending import _cast_jaccard, _overlap, _same_story, reconcile_stories

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
