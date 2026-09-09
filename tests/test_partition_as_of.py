"""The story window can be reconstructed as of a past date.

`_load_nodes`/`_load_edges`/`_load_embedding_edges` all filtered
`last_updated_at > now() - STORY_WINDOW_DAYS`. That is right for production and
fatal for measurement: a gold set stops being scoreable about a month after it is
labelled, because its events slide out of the window. Scoring the 45-story gold
set against the live partition matched 2 of 86 events and printed
P 0 / R 0 / F1 0 — which reads as a catastrophic regression rather than as an
empty join, and that is the dangerous part.

`as_of=None` must remain byte-identical to the old behaviour, since production
passes nothing and the story layer is the most delicate code in the repo.
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
import pytest_asyncio
from sqlalchemy import text

from common.db import session_scope
from correlation.partition import (
    _load_edges,
    _load_embedding_edges,
    _load_nodes,
    _window,
    merge_edges,
)
from correlation.threads import STORY_WINDOW_DAYS

TITLE = "as-of-window-probe"


@pytest_asyncio.fixture(autouse=True, loop_scope="session")
async def _cleanup():
    """Delete what this module seeds — it shares the developer's database.

    loop_scope matches the module mark; without it asyncpg tears the connection
    down across loops and the failure looks unrelated to this file.
    """
    yield
    async with session_scope() as s:
        await s.execute(text("DELETE FROM events WHERE title = :t"), {"t": TITLE})


async def _seed(s, days_ago: float) -> uuid.UUID:
    eid = uuid.uuid4()
    await s.execute(
        text("INSERT INTO events (id,title,summary,last_updated_at) "
             "VALUES (:i,:t,'s', now() - make_interval(mins => :m))"),
        {"i": str(eid), "t": TITLE, "m": int(days_ago * 24 * 60)},
    )
    return eid


@pytest.mark.asyncio(loop_scope="session")
async def test_as_of_none_keeps_the_live_window():
    async with session_scope() as s:
        fresh = await _seed(s, 1)
        stale = await _seed(s, STORY_WINDOW_DAYS + 5)
        nodes = await _load_nodes(s)
    assert str(fresh) in nodes, "a recent event must stay in the default window"
    assert str(stale) not in nodes, "as_of=None must still exclude events past the window"


@pytest.mark.asyncio(loop_scope="session")
async def test_as_of_reopens_a_window_that_has_already_slid_past():
    """The whole point: score a gold set whose events left the live window."""
    async with session_scope() as s:
        old = await _seed(s, STORY_WINDOW_DAYS + 5)
        live = await _load_nodes(s)
        past = await _load_nodes(
            s, datetime.now(UTC) - timedelta(days=STORY_WINDOW_DAYS + 4)
        )
    assert str(old) not in live, "precondition: the event is outside the live window"
    assert str(old) in past, (
        "as_of failed to reconstruct the past window, so a gold set older than "
        "STORY_WINDOW_DAYS can never be scored"
    )


@pytest.mark.asyncio(loop_scope="session")
async def test_as_of_excludes_what_had_not_happened_yet():
    """An upper bound, or `as_of` would leak the future into a past window."""
    async with session_scope() as s:
        later = await _seed(s, 1)
        past = await _load_nodes(s, datetime.now(UTC) - timedelta(days=10))
    assert str(later) not in past, (
        "an event updated after the as-of date appeared in the reconstructed "
        "window; the measurement would see data the partitioner could not have had"
    )


def test_the_upper_bound_is_guarded_rather_than_always_applied():
    sql = _window("e.last_updated_at")
    assert "IS NULL OR" in sql, "an unguarded upper bound is a tautology under now()"
    assert sql.count("coalesce") == 1


def test_merge_edges_unions_and_adds_entity_weight_where_they_agree():
    """Extracted from compute_partition; a drifted copy would score a different graph."""
    from correlation.partition import STORY_ENTITY_EDGE_WEIGHT

    out = dict(((a, b), w) for a, b, w in merge_edges(
        entity_edges=[("a", "b", 2.0), ("c", "d", 1.0)],
        emb_edges=[("a", "b", 0.5)],
    ))
    assert out[("a", "b")] == pytest.approx(0.5 + STORY_ENTITY_EDGE_WEIGHT * 2.0)
    assert out[("c", "d")] == pytest.approx(STORY_ENTITY_EDGE_WEIGHT * 1.0), (
        "an entity-only pair must survive the union; making the entity rule a "
        "gate is the v1 defect this replaced"
    )


def test_merge_edges_normalises_entity_pair_order():
    """Entity edges arrive either way round; unordered keys would double-count."""
    out = merge_edges(entity_edges=[("b", "a", 1.0)], emb_edges=[("a", "b", 0.5)])
    assert len(out) == 1, "b,a and a,b were counted as two edges"


@pytest.mark.asyncio(loop_scope="session")
async def test_every_loader_accepts_as_of_both_ways():
    """All three loaders, both call shapes — the bind-parameter wiring.

    `_window` is shared, so a predicate test passes even if a loader forgot to
    pass `:as_of` through. That omission raises only when the query runs, and the
    partitioner runs on a 15-minute cron rather than in the test suite, so it
    would surface in production. Cheap to close here.
    """
    when = datetime.now(UTC) - timedelta(days=1)
    async with session_scope() as s:
        for loader in (_load_nodes, _load_edges, _load_embedding_edges):
            await loader(s)
            await loader(s, when)
