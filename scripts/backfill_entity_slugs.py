"""Merge entity rows that fold to the same canonical slug (D.K.=DK, J.P.=JP,
'Cockroach Janta Party (CJP)'='Cockroach Janta Party'). Going forward, resolution
uses common.text.entity_slug so no new duplicates form; this cleans the existing rows.

Dry-run by default; pass `apply` to write. Re-points event_entities (dedup on the
unique (event_id, entity_id)) and impacts to the survivor, folds loser names into
survivor.aliases, then deletes the losers. Idempotent.

    uv run python scripts/backfill_entity_slugs.py          # dry run
    uv run python scripts/backfill_entity_slugs.py apply
"""

import asyncio
import sys
from collections import defaultdict

from sqlalchemy import text

from common.db import session_scope
from common.text import entity_slug


async def main(apply: bool) -> None:
    async with session_scope() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT e.id, e.name, e.slug, e.aliases,
                           (SELECT count(*) FROM event_entities ee WHERE ee.entity_id = e.id) AS links
                    FROM entities e
                    """
                )
            )
        ).mappings().all()

        groups: dict[str, list] = defaultdict(list)
        for r in rows:
            groups[entity_slug(r["name"])].append(r)
        dupes = {k: v for k, v in groups.items() if len(v) > 1}

        print(f"{len(rows)} entities | {len(dupes)} canonical groups with duplicates")
        merged = 0
        for canon, members in sorted(dupes.items(), key=lambda kv: -len(kv[1])):
            # survivor = most-linked, then lowest id (deterministic)
            members = sorted(members, key=lambda m: (-m["links"], str(m["id"])))
            survivor, losers = members[0], members[1:]
            loser_ids = [str(m["id"]) for m in losers]
            names = " | ".join(m["name"] for m in members)
            print(f"  [{ 'APPLY' if apply else 'DRY' }] {canon}: keep '{survivor['name']}' <- {names}")
            merged += len(losers)
            if not apply:
                continue
            # 1) move loser links where survivor not already linked to that event
            await session.execute(
                text(
                    """
                    UPDATE event_entities ee SET entity_id = :sv
                    WHERE ee.entity_id = ANY(CAST(:losers AS uuid[]))
                      AND NOT EXISTS (
                          SELECT 1 FROM event_entities x
                          WHERE x.event_id = ee.event_id AND x.entity_id = :sv
                      )
                    """
                ),
                {"sv": str(survivor["id"]), "losers": loser_ids},
            )
            # 2) drop the remaining loser links (would violate the unique constraint)
            await session.execute(
                text("DELETE FROM event_entities WHERE entity_id = ANY(CAST(:losers AS uuid[]))"),
                {"losers": loser_ids},
            )
            # 3) impacts has no (event,entity) unique — plain re-point
            await session.execute(
                text("UPDATE impacts SET entity_id = :sv WHERE entity_id = ANY(CAST(:losers AS uuid[]))"),
                {"sv": str(survivor["id"]), "losers": loser_ids},
            )
            # 4) delete losers FIRST (a loser may currently hold the canonical slug,
            #    so the survivor's slug update below would collide with it otherwise)
            await session.execute(
                text("DELETE FROM entities WHERE id = ANY(CAST(:losers AS uuid[]))"),
                {"losers": loser_ids},
            )
            # 5) remember the variant spellings as aliases; set the canonical slug
            alias_set = set(survivor["aliases"] or []) | {m["name"] for m in losers}
            await session.execute(
                text("UPDATE entities SET slug = :canon, aliases = CAST(:al AS text[]) WHERE id = :sv"),
                {"canon": canon, "al": sorted(alias_set), "sv": str(survivor["id"])},
            )
        print(f"\n{'MERGED' if apply else 'WOULD MERGE'} {merged} duplicate entity rows across {len(dupes)} groups")


if __name__ == "__main__":
    asyncio.run(main(apply=len(sys.argv) > 1 and sys.argv[1] == "apply"))
