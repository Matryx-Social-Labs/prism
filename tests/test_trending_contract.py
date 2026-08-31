"""The trending routes' shape, checked against the TypeScript that consumes it.

`/api/v1/trending` and `/trending/{slug}` served bare dicts. The only written
description of what they return lived in `web/src/lib/api.ts`, so the two could
drift apart and nothing in either language would notice — and these feed
`StoryTimeline` and `BranchTree`, the two most structural screens in the product.

Adding a `response_model` fixes that and introduces a sharper failure at the same
time: FastAPI DROPS any field the model does not declare, with no error. A model
missing `why` would simply stop serving the causal notes (563 of them in
production) and every test that only checks status codes would still pass.

So these tests read the TypeScript interfaces and compare field names directly.
A field added on one side and not the other fails here, in the language that
noticed first.
"""

import re
import uuid
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from api.main import app
from api.schemas import (
    BranchNodeOut,
    BranchShapeOut,
    BranchTreeOut,
    StoryDevelopmentOut,
    TrendingStoryDetail,
    TrendingStoryOut,
)
from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")

API_TS = Path(__file__).resolve().parents[1] / "web" / "src" / "lib" / "api.ts"


def ts_fields(interface: str) -> set[str]:
    """Field names of one `export interface` in api.ts.

    Deliberately simple: these interfaces are flat `name: type;` lines. Anything
    it cannot parse shows up as a missing field and fails loudly rather than
    quietly shrinking the set it compares — a parser that returned nothing would
    make every test below vacuous.
    """
    body = re.search(
        rf"export interface {interface} \{{(.*?)^\}}", API_TS.read_text(), re.S | re.M
    )
    assert body, f"{interface} not found in {API_TS.name}"
    return {
        m.group(1)
        for line in body.group(1).splitlines()
        if not line.strip().startswith(("//", "*", "/*"))
        and (m := re.match(r"\s*(\w+)\??\s*:", line))
    }


# --- the two languages must describe the same object --------------------------


@pytest.mark.parametrize(
    "model,interface",
    [
        (TrendingStoryOut, "TrendingStory"),
        (TrendingStoryDetail, "TrendingStoryDetail"),
        (StoryDevelopmentOut, "StoryDevelopment"),
        (BranchNodeOut, "BranchNode"),
    ],
)
async def test_the_served_model_and_the_typescript_agree(model, interface):
    assert set(model.model_fields) == ts_fields(interface), (
        f"{model.__name__} and {interface} have drifted; a field only Python declares "
        "is served and unread, and a field only TypeScript declares reads as undefined"
    )


async def test_the_branch_tree_matches_too():
    """`BranchTreeData` nests `shape` inline rather than naming an interface, so it
    is compared in two pieces."""
    assert set(BranchTreeOut.model_fields) == ts_fields("BranchTreeData")
    shape = re.search(r"shape: \{([^}]*)\}", API_TS.read_text())
    assert shape
    assert set(BranchShapeOut.model_fields) == {
        m.group(1) for part in shape.group(1).split(";") if (m := re.match(r"\s*(\w+)\s*:", part))
    }


# --- and both must match what the producer actually builds --------------------


async def test_every_field_the_timeline_produces_survives_the_model():
    """`correlation/threads.py` builds these dicts. A key it emits that the model
    omits is dropped on the way out — the failure mode this file exists for."""
    produced = {"id", "title", "sector", "occurred_at", "image_url", "is_current", "why"}
    assert produced <= set(StoryDevelopmentOut.model_fields)


async def test_every_field_the_branch_tree_produces_survives_the_model():
    assert {"root_id", "nodes", "shape"} <= set(BranchTreeOut.model_fields)
    assert {"id", "parent_id", "off_spine", "depth"} <= set(BranchNodeOut.model_fields)
    assert {"developments", "branches", "satellites", "max_depth"} <= set(
        BranchShapeOut.model_fields
    )


# --- served for real, over HTTP -----------------------------------------------


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def test_a_served_story_carries_every_declared_key():
    """End to end through the app. Asserts the KEYS, not just a 200: a response
    model that silently dropped half the object would still return 200 with a
    body the client renders as a blank story.
    """
    if not await _db_reachable():
        pytest.skip("no database")
    eid, sid, slug = uuid.uuid4(), uuid.uuid4(), f"contract-{uuid.uuid4().hex[:8]}"
    try:
        async with session_scope() as s:
            await s.execute(
                text(
                    # Backdated: these feeds are recency-ordered, and a row stamped
                    # now() sorts to the top of every other test's assertions.
                    "INSERT INTO events (id, title, sector, regions, "
                    "first_seen_at, last_updated_at) "
                    "VALUES (:i, 'A contract story', 'politics', '{}', "
                    "'2019-01-01', '2019-01-01')"
                ),
                {"i": str(eid)},
            )
            await s.execute(
                text(
                    'INSERT INTO stories (id, slug, label, "cast", member_event_ids, '
                    "hero_event_id, sector, regions, source_count, velocity, status, "
                    "first_seen_at, last_updated_at) "
                    "VALUES (:i, :s, 'A contract story', CAST('[\"Someone\"]' AS jsonb), "
                    "CAST(:m AS jsonb), :e, 'politics', '{}', 2, 1, 'active', "
                    "'2019-01-01', '2019-01-01')"
                ),
                {"i": str(sid), "s": slug, "m": f'["{eid}"]', "e": str(eid)},
            )

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            detail = await c.get(f"/api/v1/trending/{slug}")
            listing = await c.get("/api/v1/trending?limit=50")

        # Compared against the TYPESCRIPT, not against the model that produced the
        # body. Checking the served keys against `model_fields` is self-referential:
        # delete a field from the model and both sides lose it together, so the
        # assertion holds while the client silently receives one field fewer.
        assert detail.status_code == 200, detail.text
        assert set(detail.json()) == ts_fields("TrendingStoryDetail")
        assert detail.json()["canonical_slug"] == slug

        assert listing.status_code == 200
        served = {s["slug"]: s for s in listing.json()["stories"]}
        if slug in served:  # ranked list; a busy dev DB may push it past the limit
            assert set(served[slug]) == ts_fields("TrendingStory")
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM stories WHERE id = :i"), {"i": str(sid)})
            await s.execute(text("DELETE FROM events WHERE id = :i"), {"i": str(eid)})
