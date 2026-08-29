"""A fold must be undoable, including the rows it deletes rather than repoints.

The fold does two different things to a variant's mentions: it repoints the ones
that fit, and it DELETES the ones that would collide with a mention the canonical
already has. So a journal of row ids alone cannot restore a fold — replaying it
would UPDATE nothing for exactly the rows that were removed, finish without error,
and leave those mentions gone. A rollback that appears to work is worse than none,
because it gets trusted.

The collision case is therefore the point of this file, not an edge case in it.
"""

import json
import re
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from common.config import get_settings
from common.db import session_scope
from tools.link_entities import fold, unfold

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def _db_reachable() -> bool:
    try:
        async with session_scope() as s:
            await s.execute(text("SELECT 1"))
        return True
    except (SQLAlchemyError, OSError):
        return False


async def _conn():
    """asyncpg, because fold/unfold speak asyncpg — the driver the tools use."""
    import asyncpg

    url = re.sub(r"^postgresql\+asyncpg://", "postgresql://", get_settings().database_url)
    return await asyncpg.connect(url, timeout=30)


async def _setup(c) -> dict:
    """Both fold cases in one fixture.

    The fold makes the row with the MOST links canonical, so the canonical here
    holds three events and the variant two. Of the variant's two:

        solo    named only by the variant   -> repointed
        shared  named by BOTH               -> collides, so the row is deleted

    The deleted one is what an id-only journal could never restore.
    """
    canon, variant = uuid.uuid4(), uuid.uuid4()
    solo, shared = uuid.uuid4(), uuid.uuid4()
    only_a, only_b = uuid.uuid4(), uuid.uuid4()
    for eid, slug in ((canon, "canon"), (variant, "variant")):
        await c.execute(
            "INSERT INTO entities (id, slug, name, entity_type)"
            " VALUES ($1, $2, $3, 'organization')",
            eid, f"{slug}-{eid.hex[:8]}", f"{slug} {eid.hex[:8]}")
    for ev in (solo, shared, only_a, only_b):
        await c.execute(
            "INSERT INTO events (id, title, first_seen_at, last_updated_at)"
            " VALUES ($1, $2, now(), now())", ev, f"ev {ev.hex[:8]}")
    for ev, ent in (
        (only_a, canon), (only_b, canon), (shared, canon),   # canonical: df 3
        (solo, variant), (shared, variant),                   # variant:   df 2
    ):
        await c.execute(
            "INSERT INTO event_entities (id, event_id, entity_id, role)"
            " VALUES ($1, $2, $3, 'affected')",
            uuid.uuid4(), ev, ent)
    return {"canon": canon, "variant": variant, "solo": solo, "shared": shared,
            "only_a": only_a, "only_b": only_b}


async def _links(c, ent: uuid.UUID) -> set[uuid.UUID]:
    rows = await c.fetch("SELECT event_id FROM event_entities WHERE entity_id = $1", ent)
    return {r["event_id"] for r in rows}


async def test_fold_then_unfold_restores_both_repointed_and_deleted_rows(tmp_path: Path):
    if not await _db_reachable():
        pytest.skip("no database")
    c = await _conn()
    try:
        ids = await _setup(c)
        before_canon = await _links(c, ids["canon"])
        before_variant = await _links(c, ids["variant"])
        assert len(before_variant) == 2, "setup did not create the collision case"

        ents = [
            {"id": ids["canon"], "slug": "canon", "name": "canon", "df": 3},
            {"id": ids["variant"], "slug": "variant", "name": "variant", "df": 2},
        ]
        linked = {ids["canon"]: ("Q_TEST", "alias_exact"),
                  ids["variant"]: ("Q_TEST", "alias_exact")}
        journal = str(tmp_path / "fold.json")

        await fold(c, ents, linked, journal, write=True)

        # The canonical absorbed both events; the variant holds nothing, and the
        # redirect is set so ingest cannot reopen the split.
        assert await _links(c, ids["canon"]) == {
            ids["only_a"], ids["only_b"], ids["shared"], ids["solo"]
        }, "the repointed mention did not land on the canonical"
        assert await _links(c, ids["variant"]) == set()
        assert await c.fetchval(
            "SELECT merged_into FROM entities WHERE id = $1", ids["variant"]
        ) == ids["canon"]

        # The journal must carry whole rows — an id-only journal is what makes the
        # deleted row unrecoverable.
        doc = json.load(open(journal))
        assert doc["format"] == "prism-entity-fold/2"
        assert all("entity_id" in e["row"] for e in doc["entries"])

        await unfold(c, journal, write=True)

        assert await _links(c, ids["variant"]) == before_variant, "the deleted row was lost"
        assert await _links(c, ids["canon"]) == before_canon
        assert await c.fetchval(
            "SELECT merged_into FROM entities WHERE id = $1", ids["variant"]
        ) is None, "redirect survived the unfold; ingest would still merge"
    finally:
        await c.close()


async def test_unfold_refuses_a_journal_it_cannot_fully_restore(tmp_path: Path):
    """An older journal stored only row ids. Replaying it would silently no-op for
    every deleted row and report success, so it must be refused outright."""
    if not await _db_reachable():
        pytest.skip("no database")
    journal = tmp_path / "old.json"
    journal.write_text(json.dumps([{"table": "event_entities", "id": str(uuid.uuid4()),
                                    "from": str(uuid.uuid4()), "to": str(uuid.uuid4())}]))
    c = await _conn()
    try:
        with pytest.raises(SystemExit, match="prism-entity-fold/2"):
            await unfold(c, str(journal), write=False)
    finally:
        await c.close()
