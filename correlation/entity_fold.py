"""Fold one entity row into another, and undo it.

The mechanics tools/link_entities.py introduced for Wikidata folds, shared with
the spelling-variant fold (correlation/variants.py, tools/entity_variants.py).
asyncpg, like the tools: the consumer opens a connection only when it folds.

A fold repoints every mention of the variant onto the survivor — all six IDF
sites key on `entity_id`, so one real-world entity has to BE one row — and sets
`merged_into`, the redirect ingest follows (consumer._follow_merge) so the next
article naming the variant lands on the survivor instead of reopening the split.

A repoint is unrecoverable on its own: `article_entities` stores no surface form,
and a mention that would collide with one the survivor already holds is DELETED
((key, entity_id) is unique). So the whole of every row that moves is journalled
first; `restore` re-inserts the deleted ones and repoints the rest.
"""

import json
import uuid

JOURNAL_FORMAT = "prism-entity-fold/2"

# Mention tables keyed (key, entity_id) unique; impacts carry no such constraint.
_MENTIONS = (("event_entities", "event_id"), ("article_entities", "article_id"))


async def journal(c, variant_id: uuid.UUID, survivor_id: uuid.UUID) -> list[dict]:
    """Every row the fold of `variant_id` will touch, whole, before it touches it.

    Rows already redirected to the variant are journalled too: the fold points
    them at the survivor, because clustering follows `merged_into` one hop only
    (`_match_by_entities`), so a chain would hide the survivor from the matcher.
    """
    entries = []
    for tbl in ("event_entities", "article_entities", "impacts"):
        for r in await c.fetch(f"SELECT * FROM {tbl} WHERE entity_id = $1", variant_id):
            row = {k: (str(x) if x is not None else None) for k, x in dict(r).items()}
            entries.append({"table": tbl, "row": row, "to": str(survivor_id)})
    for r in await c.fetch("SELECT id FROM entities WHERE merged_into = $1", variant_id):
        entries.append({"table": "entities", "row": {"id": str(r["id"]), "merged_into": str(variant_id)},
                        "to": str(survivor_id)})
    return entries


async def fold_into(c, variant_id: uuid.UUID, survivor_id: uuid.UUID) -> None:
    """Repoint the variant's mentions onto the survivor and set the redirect.
    The caller owns the transaction, and journals first."""
    for tbl, key in _MENTIONS:
        # Repoint only where it would not collide with a row the survivor already
        # holds, then clear the rest.
        await c.execute(
            f"""UPDATE {tbl} SET entity_id = $1 WHERE entity_id = $2
                AND NOT EXISTS (SELECT 1 FROM {tbl} t2
                                WHERE t2.{key} = {tbl}.{key} AND t2.entity_id = $1)""",
            survivor_id, variant_id)
        await c.execute(f"DELETE FROM {tbl} WHERE entity_id = $1", variant_id)
    await c.execute("UPDATE impacts SET entity_id = $1 WHERE entity_id = $2", survivor_id, variant_id)
    await c.execute("UPDATE entities SET merged_into = $1 WHERE merged_into = $2", survivor_id, variant_id)
    # The redirect, without which the fold decays: the variant row survives (other
    # tables reference it, and it holds a name real articles use), so ingest would
    # send the next article naming it straight back here.
    await c.execute("UPDATE entities SET merged_into = $1 WHERE id = $2", survivor_id, variant_id)


async def restore(c, entries: list[dict]) -> int:
    """Undo a fold from its journal. The caller owns the transaction.

    A repointed row still exists with the survivor's entity_id, so the original is
    put back; a deleted one is re-inserted verbatim. `json_populate_record` lets
    Postgres coerce each journalled string against the table's own row type, so
    this stays correct when a column is added. The redirect is cleared too, or
    ingest would keep merging what the data no longer does.
    """
    restored = 0
    for e in entries:
        if e["table"] == "entities":
            await c.execute("UPDATE entities SET merged_into = $2 WHERE id = $1",
                            uuid.UUID(e["row"]["id"]), uuid.UUID(e["row"]["merged_into"]))
        else:
            await c.execute(
                f"INSERT INTO {e['table']} SELECT * FROM json_populate_record(NULL::{e['table']}, $1::json)"
                f" ON CONFLICT (id) DO UPDATE SET entity_id = EXCLUDED.entity_id",
                json.dumps(e["row"]),
            )
        restored += 1
    await c.execute(
        "UPDATE entities SET merged_into = NULL WHERE id = ANY($1::uuid[])",
        sorted({e["row"]["entity_id"] for e in entries if e["table"] != "entities"}),
    )
    return restored
