"""Retention must not delete a run another run is built on.

partition_runs references ITSELF: an overlay carries the base_run_id it refined.
That self-FK is NO ACTION where the other two are CASCADE and SET NULL, so
pruning an old base while a newer overlay still pointed at it raised
ForeignKeyViolationError — and since retention is deterministic it raised on the
SAME row every 15 minutes for days, taking the partition pass down with it and
leaving the grounded veto stuck at 'pending'.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope
from correlation.partition import _prune_runs

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _run(s, rid, *, base=None, status="superseded", age_days=0):
    await s.execute(
        text("INSERT INTO partition_runs (id, base_run_id, status, veto_state, resolution, stats, created_at) "
             "VALUES (:i,:b,:st,'pending',1.0,'{}'::jsonb, now() - make_interval(days => :d))"),
        {"i": str(rid), "b": str(base) if base else None, "st": status, "d": age_days},
    )


async def test_pruning_keeps_a_base_its_overlay_still_references():
    if not await _db_reachable():
        pytest.skip("no database")
    base, overlay = uuid.uuid4(), uuid.uuid4()
    ids = [str(base), str(overlay)]
    try:
        async with session_scope() as s:
            # The base is the OLDEST row, so retention wants it gone first; the
            # overlay that refined it is newer and stays. That is the live shape.
            await _run(s, base, age_days=30)
            await _run(s, overlay, base=base, age_days=1)

        async with session_scope() as s:
            await _prune_runs(s, keep=0)  # prune everything retention would allow

        async with session_scope() as s:
            left = set(
                (await s.execute(
                    text("SELECT id::text FROM partition_runs WHERE id = ANY(CAST(:i AS uuid[]))"),
                    {"i": ids},
                )).scalars().all()
            )
        # The base is what matters: it is the OLDEST row, so retention reaches it
        # first, and only the overlay's reference holds it back. The overlay is
        # itself unreferenced and prunable in this same pass — correct, and
        # test_the_base_becomes_prunable_once_its_overlay_ages_out covers the
        # order the two leave in.
        assert str(base) in left, "deleted a base that an overlay is still built on"
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM partition_runs WHERE id = ANY(CAST(:i AS uuid[]))"), {"i": ids})


async def test_an_unreferenced_old_run_is_still_pruned():
    """The guard must not turn retention into a no-op."""
    if not await _db_reachable():
        pytest.skip("no database")
    lonely = uuid.uuid4()
    try:
        async with session_scope() as s:
            await _run(s, lonely, age_days=30)
        async with session_scope() as s:
            await _prune_runs(s, keep=0)
        async with session_scope() as s:
            still = (await s.execute(
                text("SELECT count(*) FROM partition_runs WHERE id = :i"), {"i": str(lonely)}
            )).scalar()
        assert still == 0, "retention stopped pruning anything"
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM partition_runs WHERE id = :i"), {"i": str(lonely)})


async def test_the_base_becomes_prunable_once_its_overlay_ages_out():
    """Self-healing: retaining the base is a deferral, not a leak."""
    if not await _db_reachable():
        pytest.skip("no database")
    base, overlay = uuid.uuid4(), uuid.uuid4()
    ids = [str(base), str(overlay)]
    try:
        async with session_scope() as s:
            await _run(s, base, age_days=30)
            await _run(s, overlay, base=base, age_days=29)
        async with session_scope() as s:
            await _prune_runs(s, keep=0)      # overlay goes, base held
        async with session_scope() as s:
            await _prune_runs(s, keep=0)      # base is now unreferenced
        async with session_scope() as s:
            left = (await s.execute(
                text("SELECT count(*) FROM partition_runs WHERE id = ANY(CAST(:i AS uuid[]))"), {"i": ids}
            )).scalar()
        assert left == 0, "base never became prunable — this would leak rows forever"
    finally:
        async with session_scope() as s:
            await s.execute(text("DELETE FROM partition_runs WHERE id = ANY(CAST(:i AS uuid[]))"), {"i": ids})
