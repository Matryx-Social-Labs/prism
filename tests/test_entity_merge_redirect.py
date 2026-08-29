"""Ingest must follow an entity fold, or canonicalization decays as fast as it runs.

Folding "BJP" into "Bharatiya Janata Party" repoints existing mentions but keeps
the variant row — other tables reference it and it still holds a name real
articles used. So `_resolve_entity` has to follow `merged_into`; without that the
next article naming BJP lands back on the variant and the split reopens, while the
one-off measurement still reports it fixed. That is the failure this file exists
to prevent: not a crash, a quiet return to the old behaviour.

Needs Postgres — the logic under test IS the traversal, so a fake session would
assert nothing about it.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.db import session_scope

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _entity(s, name: str, *, merged_into: uuid.UUID | None = None) -> uuid.UUID:
    """A person entity with a unique slug, so repeat runs cannot collide."""
    eid = uuid.uuid4()
    await s.execute(
        text(
            "INSERT INTO entities (id, slug, name, entity_type, merged_into)"
            " VALUES (:i, :s, :n, 'person', :m)"
        ),
        {"i": str(eid), "s": f"{name}-{eid.hex[:8]}",
         "n": f"{name} {eid.hex[:8]}", "m": merged_into},
    )
    return eid


async def _name_of(s, eid: uuid.UUID) -> str:
    row = await s.execute(text("SELECT name FROM entities WHERE id = :i"), {"i": eid})
    return row.scalar_one()


async def test_resolve_follows_a_fold_to_the_canonical_row():
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.consumer import _resolve_entity

    async with session_scope() as s:
        canon = await _entity(s, "canonical")
        variant = await _entity(s, "variant", merged_into=canon)
        got = await _resolve_entity(s, await _name_of(s, variant))
        assert got == canon, "a folded name resolved back to the variant — the split reopens"


async def test_an_unfolded_entity_resolves_to_itself():
    """The overwhelmingly common path: merged_into is NULL for almost every row,
    and must behave exactly as it did before this column existed."""
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.consumer import _resolve_entity

    async with session_scope() as s:
        eid = await _entity(s, "plain")
        assert await _resolve_entity(s, await _name_of(s, eid)) == eid


async def test_a_two_hop_chain_lands_on_the_end():
    """One hop was 'obviously' enough for stories too, until a production audit
    found a two-hop chain among 356 merged rows and share links resolved to a dead
    story. Same structure here, so the same assumption is not made twice."""
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.consumer import _resolve_entity

    async with session_scope() as s:
        end = await _entity(s, "end")
        mid = await _entity(s, "mid", merged_into=end)
        start = await _entity(s, "start", merged_into=mid)
        assert await _resolve_entity(s, await _name_of(s, start)) == end


async def test_a_cycle_terminates_instead_of_hanging():
    """Corruption must fail safe. A `while` here would spin forever inside the
    ingest worker and take the stage down — far worse than returning a
    merely-imperfect entity."""
    if not await _db_reachable():
        pytest.skip("no database")
    from correlation.consumer import _resolve_entity

    async with session_scope() as s:
        a = await _entity(s, "cyca")
        b = await _entity(s, "cycb", merged_into=a)
        await s.execute(
            text("UPDATE entities SET merged_into = :b WHERE id = :a"), {"a": a, "b": b}
        )
        assert await _resolve_entity(s, await _name_of(s, b)) in (a, b)


async def test_the_database_refuses_a_pointer_to_a_row_that_does_not_exist():
    """Why `_resolve_entity`'s dangling-pointer branch is defence, not a code path.

    The foreign key makes an unresolvable `merged_into` impossible to write, which
    is the real guarantee — the branch exists only so corruption degrades to the
    unfolded row instead of raising on a None unpack. This asserts the constraint
    rather than the branch, because trying to reach the branch means first writing
    a row the schema is designed to reject.
    """
    if not await _db_reachable():
        pytest.skip("no database")
    with pytest.raises(SQLAlchemyError):
        async with session_scope() as s:
            await _entity(s, "orphan", merged_into=uuid.uuid4())
