"""Read side of the L3 branch tree: event_story.branch_parent_id / off_spine.

partition.py has been writing these columns every run since the storyline
partitioner shipped and nothing has ever read them. These tests pin the shape the
trending storyline page depends on, and the two cases that are easy to get wrong:
a frozen member set that cuts a parent off, and the counted shape readout.

DB-backed, skipped when unreachable (same convention as test_partition.py).
"""

import contextlib
import datetime as dt
import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from correlation.threads import branch_tree_for_members

pytestmark = pytest.mark.asyncio(loop_scope="session")
UTC = dt.UTC


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


@contextlib.asynccontextmanager
async def _story(shape: list[tuple[int, int | None, bool]]):
    """Build a partition run whose story is `shape` = [(idx, parent_idx|None, off_spine)].

    Tears itself down on exit. There is no test database here — DATABASE_URL is
    the developer's own — so a test that inserts and walks away pollutes the dev
    feed with fake developments. Worse, making a run 'current' requires retiring
    the existing one (partial-unique index), which detaches the real storylines
    the local trending page reads. Both get restored below.
    """
    ids = [uuid.uuid4() for _ in shape]
    run_id = uuid.uuid4()
    async with session_scope() as s:
        for i, eid in enumerate(ids):
            await s.execute(
                text("INSERT INTO events (id,title,summary,last_updated_at) VALUES (:i,:t,'s',now())"),
                {"i": str(eid), "t": f"development {i}"},
            )
        prior = (
            await s.execute(text("SELECT id FROM partition_runs WHERE status='current'"))
        ).scalar()
        # Only one run may be 'current' (partial-unique index), so retire the rest.
        await s.execute(text("UPDATE partition_runs SET status='superseded' WHERE status='current'"))
        await s.execute(
            text("INSERT INTO partition_runs (id,status,created_at) VALUES (:r,'current',now())"),
            {"r": str(run_id)},
        )
        for idx, parent_idx, off in shape:
            await s.execute(
                text(
                    "INSERT INTO event_story (run_id,event_id,story_label,branch_parent_id,off_spine) "
                    "VALUES (:r,:e,1,:p,:o)"
                ),
                {
                    "r": str(run_id),
                    "e": str(ids[idx]),
                    "p": str(ids[parent_idx]) if parent_idx is not None else None,
                    "o": off,
                },
            )
    try:
        yield ids, run_id
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM event_story WHERE run_id = :r"), {"r": str(run_id)})
            await s.execute(text("DELETE FROM partition_runs WHERE id = :r"), {"r": str(run_id)})
            await s.execute(
                text("DELETE FROM events WHERE id = ANY(CAST(:e AS uuid[]))"),
                {"e": [str(i) for i in ids]},
            )
            if prior:  # hand the dev's real storylines back
                await s.execute(
                    text("UPDATE partition_runs SET status='current' WHERE id = :p"),
                    {"p": str(prior)},
                )


async def test_returns_none_when_story_predates_the_current_run():
    if not await _db_reachable():
        pytest.skip("no database")
    # Unknown members → None, so the client keeps rendering the flat timeline.
    assert await branch_tree_for_members([str(uuid.uuid4())]) is None
    assert await branch_tree_for_members([]) is None


async def test_reads_the_tree_with_depth_and_root():
    if not await _db_reachable():
        pytest.skip("no database")
    #   0 (root)
    #   ├─ 1
    #   │  └─ 3
    #   └─ 2
    async with _story([(0, None, False), (1, 0, False), (2, 0, False), (3, 1, False)]) as (ids, _):
        tree = await branch_tree_for_members([str(i) for i in ids])
        assert tree is not None
        assert tree["root_id"] == str(ids[0])

        depth = {n["id"]: n["depth"] for n in tree["nodes"]}
        assert depth[str(ids[0])] == 0
        assert depth[str(ids[1])] == 1
        assert depth[str(ids[2])] == 1
        assert depth[str(ids[3])] == 2  # grandchild
        assert tree["shape"]["max_depth"] == 2
        assert tree["shape"]["developments"] == 4


async def test_frozen_member_set_reattaches_orphans_instead_of_dropping_them():
    if not await _db_reachable():
        pytest.skip("no database")
    # The slug pins the member set it EARNED. If a parent isn't in that set, the
    # child must survive — dropping it would silently lose a development the page
    # is already listing in its timeline.
    async with _story([(0, None, False), (1, 0, False), (2, 1, False)]) as (ids, _):
        frozen = [str(ids[0]), str(ids[2])]  # ids[1], the middle parent, is cut out

        tree = await branch_tree_for_members(frozen)
        assert tree is not None
        assert {n["id"] for n in tree["nodes"]} == set(frozen)  # nothing dropped
        orphan = next(n for n in tree["nodes"] if n["id"] == str(ids[2]))
        assert orphan["parent_id"] is None  # re-attached, not left pointing at a ghost
        assert orphan["depth"] == 0


async def test_shape_readout_counts_forks_and_satellites():
    if not await _db_reachable():
        pytest.skip("no database")
    #   0 (root) ├─ 1  ├─ 2 (satellite)   └─ 3      — root has 3 children => a fork
    async with _story([(0, None, False), (1, 0, False), (2, 0, True), (3, 0, False)]) as (ids, _):
        tree = await branch_tree_for_members([str(i) for i in ids])
        shape = tree["shape"]
        assert shape["developments"] == 4
        assert shape["satellites"] == 1             # off_spine is surfaced, not hidden
        assert shape["branches"] == 3               # every child of a multi-child parent

    # A straight chain is NOT a branch — the readout must not claim structure the
    # data doesn't have, since the whole point is that it is counted, not inferred.
    async with _story([(0, None, False), (1, 0, False), (2, 1, False)]) as (ids2, _):
        chain = await branch_tree_for_members([str(i) for i in ids2])
        assert chain["shape"]["branches"] == 0
        assert chain["shape"]["satellites"] == 0


async def test_setup_failure_hands_the_current_run_back():
    """The fixture retires the developer's current partition run BEFORE its yield,
    and `finally` only covers what happens after it. A setup that died in between
    would leave this database with no current run at all — every storyline the
    local trending page reads, detached, by a test that never ran.

    It doesn't, but only because the retire and the inserts share one
    transaction and session_scope rolls back on the way out. That is the property
    worth pinning: it breaks the moment anyone commits mid-setup.
    """
    if not await _db_reachable():
        pytest.skip("no database")

    async def snapshot() -> tuple[uuid.UUID | None, int]:
        async with session_scope() as s:
            run = (await s.execute(text("SELECT id FROM partition_runs WHERE status='current'"))).scalar()
            events = (await s.execute(text("SELECT count(*) FROM events"))).scalar()
            return run, events

    before = await snapshot()
    # A parent index no shape row can satisfy: dies inside setup, after the retire.
    with pytest.raises(IndexError):
        async with _story([(0, 9, False)]):
            pass  # never reached

    assert await snapshot() == before, "a failed fixture setup left the database changed"
