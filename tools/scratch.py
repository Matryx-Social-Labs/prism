"""Replay clustering through the REAL matcher, in a local scratch schema.

tools/repair.py re-decided clustering with a Python reimplementation of the match
cascade, and that reimplementation drifted from the real one three times — each
time proposing a split that would have destroyed a legitimate story. A second
implementation of the thing you are repairing is a liability.

So this calls `correlation.clustering.find_event` itself. Production rows are
copied into a scratch schema in the LOCAL database, the events under repair are
removed from it, and their articles are replayed in arrival order exactly as the
correlation consumer would. Whatever the matcher does, this does, because it is
the matcher.

  SET search_path = repair_scratch, public

is what makes that work: find_event's SQL names `events`, `entities` and the rest
unqualified, so they resolve to the scratch copies, while `similarity()` and the
pgvector `<=>` operator still resolve to the extensions in public.

Production is opened READ ONLY here and never written. This tool only reports;
tools/repair.py --split remains the thing that applies a decision.

  uv run python -m tools.scratch                    # all over-merged events
  uv run python -m tools.scratch --event <uuid>
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import subprocess
import uuid

import asyncpg
from sqlalchemy import text as sa_text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from common.text import entity_slug
from correlation.clustering import ENTITY_MATCH_TYPES, find_event

SCRATCH = "repair_scratch"
OVER_MERGE_MIN = 20

# Only the columns the matcher reads. Constraints are deliberately NOT copied —
# scratch has no `sources` table, and a foreign key to one would be a copy of
# production's shape rather than of its behaviour.
COLUMNS = {
    "events": "id, title, sector, occurred_at, last_updated_at, embedding, projection",
    "entities": "id, slug, name, entity_type",
    "event_entities": "id, event_id, entity_id, role",
    "event_memberships": "id, event_id, article_id, match_type, is_survivor",
    "articles": "id, raw_item_id, clean_text, retrieval_tier, word_count",
    "raw_items": "id, source_id, external_id, url, title, raw, relevance, published_at",
}


def _prod_url() -> str:
    raw = os.environ.get("REPAIR_DATABASE_URL")
    if not raw:
        out = subprocess.run(
            ["railway", "variables", "--service", "Postgres", "--kv"],
            capture_output=True, text=True, timeout=60,
        ).stdout
        for line in out.splitlines():
            if line.startswith("DATABASE_URL="):
                raw = line.split("=", 1)[1].strip()
                break
    if not raw:
        raise SystemExit("no production url (set REPAIR_DATABASE_URL)")
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw)


def _local_url() -> str:
    from common.config import get_settings

    url = get_settings().database_url
    host = re.search(r"@([^:/]+)", url)
    if not host or host.group(1) not in ("localhost", "127.0.0.1", "db", "postgres"):
        raise SystemExit(f"refusing to build scratch anywhere but a local database: {host}")
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", url)


async def build_scratch(prod: asyncpg.Connection, local: asyncpg.Connection, targets: list) -> None:
    print(f"building {SCRATCH} from production ...")
    await local.execute(f"DROP SCHEMA IF EXISTS {SCRATCH} CASCADE")
    await local.execute(f"CREATE SCHEMA {SCRATCH}")
    for t, cols in COLUMNS.items():
        await local.execute(f"CREATE TABLE {SCRATCH}.{t} (LIKE public.{t} INCLUDING DEFAULTS)")
        rows = await prod.fetch(f"SELECT {cols} FROM {t}")
        if not rows:
            continue
        names = [c.strip() for c in cols.split(",")]
        # asyncpg surfaces vector/jsonb as text; cast them back on the way in.
        casts = []
        for n in names:
            if n == "embedding":
                casts.append(f"${len(casts)+1}::vector")
            elif n in ("projection", "raw"):
                casts.append(f"${len(casts)+1}::jsonb")
            else:
                casts.append(f"${len(casts)+1}")
        stmt = f"INSERT INTO {SCRATCH}.{t} ({', '.join(names)}) VALUES ({', '.join(casts)})"
        await local.executemany(stmt, [tuple(r[n] for n in names) for r in rows])
        print(f"  {t:20} {len(rows):>7}")

    # Remove the events being re-decided so their articles can be replayed
    # against everything else, exactly as they were the first time.
    ids = [str(t) for t in targets]
    await local.execute(
        f"DELETE FROM {SCRATCH}.event_memberships WHERE event_id = ANY($1::uuid[])", ids
    )
    await local.execute(f"DELETE FROM {SCRATCH}.event_entities WHERE event_id = ANY($1::uuid[])", ids)
    await local.execute(f"DELETE FROM {SCRATCH}.events WHERE id = ANY($1::uuid[])", ids)
    for idx in (
        f"CREATE INDEX ON {SCRATCH}.events USING gin (title gin_trgm_ops)",
        f"CREATE INDEX ON {SCRATCH}.entities (slug)",
        f"CREATE INDEX ON {SCRATCH}.event_entities (entity_id)",
        f"CREATE INDEX ON {SCRATCH}.event_entities (event_id)",
        f"CREATE INDEX ON {SCRATCH}.event_memberships (article_id)",
        f"CREATE INDEX ON {SCRATCH}.raw_items (url)",
    ):
        await local.execute(idx)
    print(f"  removed {len(ids)} target event(s) from scratch\n")


async def replay(prod: asyncpg.Connection, local_url: str, event_id) -> dict:
    """Replay one event's articles through the real find_event."""
    members = await prod.fetch(
        """SELECT a.id aid, ri.title, ri.url, ri.published_at, a.created_at,
                  ac.embedding::text vec, e.shared_fields->'entities' ents,
                  e.model, e.lens_fields
           FROM event_memberships em
           JOIN articles a ON a.id = em.article_id
           JOIN raw_items ri ON ri.id = a.raw_item_id
           JOIN article_chunks ac ON ac.article_id = a.id AND ac.chunk_index = 0
           LEFT JOIN enrichments e ON e.article_id = a.id
           WHERE em.event_id = $1
           ORDER BY ri.published_at NULLS LAST, a.created_at, a.id""",
        event_id,
    )

    engine = create_async_engine(
        local_url.replace("postgresql://", "postgresql+asyncpg://"),
        connect_args={"server_settings": {"search_path": f"{SCRATCH},public"}},
        pool_pre_ping=True,
    )
    Session = async_sessionmaker(engine, expire_on_commit=False)
    placed: dict[str, list] = {}
    created: set[str] = set()
    try:
        for m in members:
            ents = m["ents"]
            ents = json.loads(ents) if isinstance(ents, str) else (ents or [])
            slugs = [
                entity_slug(e["name"]) for e in ents
                if e.get("name") and e.get("type") in ENTITY_MATCH_TYPES
            ]
            lens = (json.loads(m["lens_fields"]) if isinstance(m["lens_fields"], str)
                    else m["lens_fields"]) or {}
            vec = [float(x) for x in m["vec"].strip("[]").split(",")]

            async with Session() as s:
                match = await find_event(
                    s,
                    cve_ids=(lens.get("cyber") or {}).get("cve_ids") or [],
                    url=m["url"],
                    title=m["title"] or "",
                    published_at=m["published_at"],
                    embedding=vec,
                    entity_slugs=slugs or None,
                    cve_record=(m["model"] or "").startswith("deterministic:"),
                )
                if match is None:
                    # A new event, written exactly as the consumer writes one.
                    eid = uuid.uuid4()
                    created.add(str(eid))
                    await s.execute(
                        sa_text("INSERT INTO events (id,title,sector,occurred_at,last_updated_at,embedding) "
                                "VALUES (:i,:t,'politics',:o,now(),CAST(:v AS vector))"),
                        {"i": str(eid), "t": m["title"] or "", "o": m["published_at"],
                         "v": "[" + ",".join(str(x) for x in vec) + "]"},
                    )
                else:
                    eid = match.event_id
                await s.execute(
                    sa_text("INSERT INTO event_memberships (id,event_id,article_id,match_type,is_survivor) "
                            "VALUES (:i,:e,:a,:mt,false)"),
                    {"i": str(uuid.uuid4()), "e": str(eid), "a": str(m["aid"]),
                     "mt": match.match_type if match else "new_event"},
                )
                # The actors this article contributes, so the event grows its cast
                # the way it does in production.
                if slugs:
                    await s.execute(
                        sa_text("INSERT INTO event_entities (id,event_id,entity_id,role) "
                                "SELECT gen_random_uuid(), :e, ent.id, 'subject' FROM entities ent "
                                "WHERE ent.slug = ANY(CAST(:s AS text[]))"),
                        {"e": str(eid), "s": slugs},
                    )
                await s.commit()
            placed.setdefault(str(eid), []).append(m)
    finally:
        await engine.dispose()
    return placed, created


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", help="replay a single event id")
    a = ap.parse_args()

    prod = await asyncpg.connect(_prod_url(), timeout=60)
    await prod.execute("SET default_transaction_read_only = on")
    local_url = _local_url()
    local = await asyncpg.connect(local_url, timeout=60)
    try:
        if a.event:
            targets = [uuid.UUID(a.event)]
        else:
            targets = [
                r["event_id"] for r in await prod.fetch(
                    """SELECT em.event_id FROM event_memberships em GROUP BY 1
                       HAVING count(*) >= $1 ORDER BY count(*) DESC""", OVER_MERGE_MIN)
            ]
        await build_scratch(prod, local, targets)

        total_before = total_after = 0
        agg_rejoin = agg_new = 0
        for t in targets:
            placed, created = await replay(prod, local_url, t)
            sizes = sorted((len(v) for v in placed.values()), reverse=True)
            n = sum(sizes)
            total_before += n
            total_after += len(placed)
            agg_rejoin += sum(len(v) for k, v in placed.items() if k not in created)
            agg_new += sum(len(v) for k, v in placed.items() if k in created)
            biggest = max(placed.values(), key=len)
            # An article that lands on a PRE-EXISTING event has rejoined the story
            # it belonged to all along — a better outcome than a new singleton, and
            # invisible to a replay that only compares an event's members to each
            # other. Worth separating, because "10 clusters" reads very differently
            # if four of them are stories that already exist.
            rejoined = {k: v for k, v in placed.items() if k not in created}
            n_rejoin = sum(len(v) for v in rejoined.values())
            print(f"  {t}  {n} -> {len(placed)} clusters")
            print(f"    sizes: {sizes[:12]}{' ...' if len(sizes) > 12 else ''}")
            print(f"    kept:  {(biggest[0]['title'] or '')[:56]}")
            if rejoined:
                print(f"    rejoined {n_rejoin} article(s) to {len(rejoined)} EXISTING event(s):")
                for k, v in list(rejoined.items())[:4]:
                    print(f"      [{len(v)}] {(v[0]['title'] or '')[:50]}")
        print(f"\n  TOTAL: {total_before} articles in {len(targets)} events -> {total_after} events")
        print(f"    {agg_rejoin} article(s) rejoined a story that already exists")
        print(f"    {agg_new} article(s) became a new event")
        print("\n  Production was read-only throughout; this reports only.")
    finally:
        await prod.close()
        await local.close()


if __name__ == "__main__":
    asyncio.run(main())
