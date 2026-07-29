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
    # Since 0.0.81.0 the matcher derives an event's cast from the articles it
    # holds, so without this the replay would see every event with an empty
    # cast and refuse every entity match.
    "article_entities": "id, article_id, entity_id, role",
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
        f"CREATE INDEX ON {SCRATCH}.event_memberships (event_id)",
        # UNIQUE, not just an index: the replay upserts with ON CONFLICT, and
        # LIKE ... INCLUDING DEFAULTS does not carry constraints across.
        f"CREATE UNIQUE INDEX ON {SCRATCH}.article_entities (article_id, entity_id)",
        f"CREATE INDEX ON {SCRATCH}.article_entities (article_id)",
        f"CREATE INDEX ON {SCRATCH}.article_entities (entity_id)",
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
    outlets = {entity_slug(r['slug']) for r in await prod.fetch('SELECT slug FROM sources')}
    outlets |= {entity_slug(r['name']) for r in await prod.fetch('SELECT name FROM sources')}
    try:
        for m in members:
            ents = m["ents"]
            ents = json.loads(ents) if isinstance(ents, str) else (ents or [])
            # Outlets are not actors. Without this the replay writes them back
            # into the graph — which is exactly how a previous repair pushed
            # `prajavani` to 240 event links after the live path had stopped
            # producing them.
            slugs = [
                entity_slug(e["name"]) for e in ents
                if e.get("name") and e.get("type") in ENTITY_MATCH_TYPES
                and entity_slug(e["name"]) not in outlets
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
                    # and the article-level link, or the event this article just
                    # joined would not count it toward its own cast
                    await s.execute(
                        sa_text("INSERT INTO article_entities (id,article_id,entity_id,role) "
                                "SELECT gen_random_uuid(), :a, ent.id, 'subject' FROM entities ent "
                                "WHERE ent.slug = ANY(CAST(:s AS text[])) "
                                "ON CONFLICT (article_id, entity_id) DO NOTHING"),
                        {"a": str(m["aid"]), "s": slugs},
                    )
                await s.commit()
            placed.setdefault(str(eid), []).append(m)
    finally:
        await engine.dispose()
    return placed, created


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--event", help="replay a single event id")
    ap.add_argument("--plan", metavar="FILE", help="write the membership moves as a reviewable plan")
    ap.add_argument("--apply-plan", metavar="FILE", dest="apply_plan", help="execute a plan")
    ap.add_argument("--yes", action="store_true", help="WRITE. Without it, --apply-plan validates only.")
    ap.add_argument("--rehearse", action="store_true",
                    help="run the whole transaction against live rows, then roll it back")
    a = ap.parse_args()

    prod = await asyncpg.connect(_prod_url(), timeout=60)
    if a.apply_plan:
        if not (a.yes or a.rehearse):
            await prod.execute("SET default_transaction_read_only = on")
        try:
            await apply_plan(prod, json.load(open(a.apply_plan)), write=a.yes,
                             rehearse=a.rehearse)
        finally:
            await prod.close()
        return
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
        plan: dict = {"targets": [str(t) for t in targets], "create_events": [],
                      "moves": [], "retitle": []}
        runs: list = []
        for t in targets:
            placed, created = await replay(prod, local_url, t)
            runs.append((t, placed, created))
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
                for _k, v in list(rejoined.items())[:4]:
                    print(f"      [{len(v)}] {(v[0]['title'] or '')[:50]}")
        # Resolve inheritance ACROSS all targets, not per target. An event created
        # while replaying target A can be rejoined while replaying target B, so a
        # per-target remap would leave B's moves pointing at an id A had already
        # renamed. Decide every destination once, here, then emit.
        inherit: dict[str, str] = {}
        orphaned_identity: list[str] = []
        for t, placed, created in runs:
            # Identity follows the FOUNDING article, not the biggest cluster. An
            # event's title and embedding are copied from the article that created
            # it, so handing the id to a cluster that does not contain that article
            # leaves a story whose headline describes something it no longer holds.
            # The replay feeds articles in arrival order, so the founder is the
            # first one placed.
            founder = next(iter(next(iter(placed.values()))))["aid"] if placed else None
            first_aid = min(
                (m["aid"] for v in placed.values() for m in v),
                key=lambda x: str(x), default=None,
            )
            home = None
            for k, v in placed.items():
                if any(str(m["aid"]) == str(founder) for m in v):
                    home = k
                    break
            if home is not None and home in created:
                inherit[home] = str(t)
            else:
                # The founder rejoined a DIFFERENT pre-existing event, so the id
                # cannot follow it without colliding. Fall back to the largest new
                # cluster and record it — the surviving event's title will describe
                # an article that has moved on, and that is worth knowing.
                fresh = sorted(((k, v) for k, v in placed.items() if k in created),
                               key=lambda kv: -len(kv[1]))
                if fresh:
                    inherit[fresh[0][0]] = str(t)
                    orphaned_identity.append(str(t))
            _ = first_aid
        # A surviving event whose founder left must be re-titled from the earliest
        # article it actually keeps — same rule a new event is titled by. Keeping
        # the id makes shared links resolve; retitling makes what they resolve TO
        # honest. Leaving the old title would be the worst of both.
        for t, placed, _created in runs:
            home = next((k for k, v in inherit.items() if v == str(t)), None)
            if home is None or str(t) not in orphaned_identity:
                continue
            keep = sorted(placed[home], key=lambda m: (m["published_at"] or m["created_at"]))
            plan["retitle"].append({
                "event_id": str(t),
                "from_article_id": str(keep[0]["aid"]),
                "new_title": (keep[0]["title"] or "")[:120],
            })

        seen_new: set[str] = set()
        for t, placed, created in runs:
            for k, v in placed.items():
                dest = inherit.get(k, k)
                if k in created and k not in inherit and k not in seen_new:
                    seen_new.add(k)
                    plan["create_events"].append(
                        {"id": k, "founder_article_id": str(v[0]["aid"]),
                         "title": (v[0]["title"] or "")[:120]}
                    )
                for m in v:
                    plan["moves"].append(
                        {"article_id": str(m["aid"]), "from_event_id": str(t), "to_event_id": dest}
                    )

        if orphaned_identity:
            print(f"\n  NOTE: {len(orphaned_identity)} event(s) whose founding article moved to a"
                  f" different existing story; their title will describe an article they no"
                  f" longer hold:")
            for e in orphaned_identity[:6]:
                print(f"    {e}")

        if a.plan:
            with open(a.plan, "w") as fh:
                json.dump(plan, fh, indent=2, default=str)
            print(f"\n  plan written: {a.plan}"
                  f"  ({len(plan['create_events'])} events to create, {len(plan['moves'])} moves)")

        print(f"\n  TOTAL: {total_before} articles in {len(targets)} events -> {total_after} events")
        print(f"    {agg_rejoin} article(s) rejoined a story that already exists")
        print(f"    {agg_new} article(s) became a new event")
        print("\n  Production was read-only throughout; this reports only.")
    finally:
        await prod.close()
        await local.close()




# ── applying a plan ─────────────────────────────────────────────────────────

class _Rehearsed(Exception):
    """Raised to force a rollback after a full rehearsal."""


async def apply_plan(prod: asyncpg.Connection, plan: dict, *, write: bool,
                     rehearse: bool = False) -> None:
    """Execute a plan produced by --plan, in one transaction, against production.

    Validated against live state first. The plan is a SNAPSHOT: it names the event
    each article sits in at generation time, so if anything has moved since — a
    resumed worker, an earlier partial run — applying it blind would move articles
    out of events they no longer belong to. Drift aborts rather than guesses.
    """
    moves = plan["moves"]
    creates = {c["id"]: c for c in plan["create_events"]}
    retitles = plan["retitle"]
    art_ids = [m["article_id"] for m in moves]

    live = {
        str(r["article_id"]): str(r["event_id"])
        for r in await prod.fetch(
            "SELECT article_id, event_id FROM event_memberships WHERE article_id = ANY($1::uuid[])",
            art_ids,
        )
    }
    drift = [m for m in moves if live.get(m["article_id"]) != m["from_event_id"]]
    missing = [a for a in art_ids if a not in live]
    print(f"  validating {len(moves)} moves against live state ...")
    print(f"    articles not found      : {len(missing)}")
    print(f"    articles that have moved: {len(drift)}")
    if drift or missing:
        print("  ABORT — the plan no longer matches production. Regenerate it.")
        for m in drift[:5]:
            print(f"    {m['article_id'][:8]} expected in {m['from_event_id'][:8]}, "
                  f"found in {live.get(m['article_id'], 'nowhere')[:8]}")
        return

    before_total = await prod.fetchval("SELECT count(*) FROM event_memberships")
    real_moves = [m for m in moves if m["to_event_id"] != m["from_event_id"]]
    print(f"    moves that actually change something: {len(real_moves)}")
    print(f"    events to create: {len(creates)}   retitles: {len(retitles)}")
    if not write and not rehearse:
        print("\n  DRY RUN — nothing written. Add --yes to apply.")
        return

    rollback = {
        "memberships": [{"article_id": a, "event_id": e} for a, e in live.items()],
        "created_event_ids": list(creates),
        "titles": [
            {"event_id": r["event_id"], "title": t}
            for r in retitles
            for t in [await prod.fetchval("SELECT title FROM events WHERE id = $1::uuid", r["event_id"])]
        ],
    }
    path = "/tmp/repair-plan-rollback.json"
    with open(path, "w") as fh:
        json.dump(rollback, fh, indent=2)
    print(f"  rollback written: {path}")

    try:
      async with prod.transaction():
        # 1. the new events, titled and vectorised from their founding article
        for c in creates.values():
            await prod.execute(
                """INSERT INTO events (id, title, summary, sector, subsector, regions,
                                       occurred_at, embedding, last_updated_at)
                   SELECT $1::uuid, ri.title, e.summary,
                          coalesce(ri.classification->>'sector','other'),
                          ri.classification->>'subsector',
                          coalesce(ev.regions, '{}'), e.occurred_at, ac.embedding, now()
                   FROM articles a
                   JOIN raw_items ri ON ri.id = a.raw_item_id
                   JOIN article_chunks ac ON ac.article_id = a.id AND ac.chunk_index = 0
                   LEFT JOIN enrichments e ON e.article_id = a.id
                   LEFT JOIN LATERAL (SELECT regions FROM events LIMIT 0) ev ON true
                   WHERE a.id = $2::uuid
                   ON CONFLICT (id) DO NOTHING""",
                c["id"], c["founder_article_id"],
            )
        # 2. the memberships
        for m in real_moves:
            await prod.execute(
                "UPDATE event_memberships SET event_id = $1::uuid WHERE article_id = $2::uuid",
                m["to_event_id"], m["article_id"],
            )
        # 3. survivors whose founder left get the title of what they actually keep
        for r in retitles:
            await prod.execute(
                """UPDATE events SET title = ri.title, occurred_at = e.occurred_at,
                          embedding = ac.embedding, summary = e.summary, last_updated_at = now()
                   FROM articles a
                   JOIN raw_items ri ON ri.id = a.raw_item_id
                   JOIN article_chunks ac ON ac.article_id = a.id AND ac.chunk_index = 0
                   LEFT JOIN enrichments e ON e.article_id = a.id
                   WHERE a.id = $2::uuid AND events.id = $1::uuid""",
                r["event_id"], r["from_article_id"],
            )
        # 4. every touched event's cast, rebuilt from the articles it now holds —
        #    an inherited actor list is exactly what made these events magnets.
        touched = sorted({m["to_event_id"] for m in moves} | {m["from_event_id"] for m in moves})
        outlets = sorted(
            {entity_slug(r["slug"]) for r in await prod.fetch("SELECT slug FROM sources")}
            | {entity_slug(r["name"]) for r in await prod.fetch("SELECT name FROM sources")}
        )
        await prod.execute("DELETE FROM event_entities WHERE event_id = ANY($1::uuid[])", touched)
        await prod.execute(
            """INSERT INTO event_entities (id, event_id, entity_id, role)
               SELECT DISTINCT ON (em.event_id, ent.id)
                      gen_random_uuid(), em.event_id, ent.id, 'subject'
               FROM event_memberships em
               JOIN enrichments e ON e.article_id = em.article_id
               CROSS JOIN LATERAL jsonb_array_elements(e.shared_fields->'entities') x
               JOIN entities ent ON ent.name = x->>'name'
               WHERE em.event_id = ANY($1::uuid[])
                 -- Outlets are not actors. Rebuilding without this re-introduces
                 -- every link the entity cleanup removed; it is how a previous
                 -- repair pushed `prajavani` to 240 event links.
                 AND ent.slug <> ALL($2::text[])""",
            touched, outlets,
        )
        # Assert the RESULT, not just that the statements ran. A rehearsal that
        # only proves the SQL parses would have told us nothing about whether the
        # repair is correct.
        total_now = await prod.fetchval("SELECT count(*) FROM event_memberships")
        orphans = await prod.fetchval(
            "SELECT count(*) FROM articles a WHERE NOT EXISTS "
            "(SELECT 1 FROM event_memberships m WHERE m.article_id = a.id)")
        empty_targets = await prod.fetchval(
            "SELECT count(*) FROM events e WHERE e.id = ANY($1::uuid[]) AND NOT EXISTS "
            "(SELECT 1 FROM event_memberships m WHERE m.event_id = e.id)", plan["targets"])
        created_empty = await prod.fetchval(
            "SELECT count(*) FROM events e WHERE e.id = ANY($1::uuid[]) AND NOT EXISTS "
            "(SELECT 1 FROM event_memberships m WHERE m.event_id = e.id)", list(creates))
        # Three separate repairs have re-introduced something a forward-only fix
        # had already stopped, so this is asserted rather than trusted.
        outlet_links = await prod.fetchval(
            """SELECT count(*) FROM event_entities ee JOIN entities e ON e.id = ee.entity_id
               WHERE e.slug = ANY($1::text[])""", outlets)
        no_cast = await prod.fetchval(
            "SELECT count(*) FROM events e WHERE e.id = ANY($1::uuid[]) AND NOT EXISTS "
            "(SELECT 1 FROM event_entities x WHERE x.event_id = e.id)", touched)
        print(f"    memberships total     : {total_now} (was {before_total}, delta "
              f"{total_now - before_total})")
        print(f"    orphaned articles     : {orphans}")
        print(f"    original events empty : {empty_targets} of {len(plan['targets'])}")
        print(f"    created events empty  : {created_empty} of {len(creates)}")
        print(f"    touched events no cast: {no_cast} of {len(touched)}")
        print(f"    outlet entity links   : {outlet_links} (must be 0)")
        bad = (total_now != before_total or orphans or empty_targets
               or created_empty or outlet_links)
        if bad:
            print("    RESULT FAILED ITS OWN CHECKS — rolling back regardless of --yes.")
            raise _Rehearsed

        if rehearse:
            # Every statement has now run against real rows. Undo it: a rehearsal
            # that commits is just an apply with extra steps.
            raise _Rehearsed
    except _Rehearsed:
        print("  REHEARSED: every statement executed against live rows, then rolled back.")
        return
    print(f"  APPLIED: {len(creates)} events created, {len(real_moves)} memberships moved, "
          f"{len(retitles)} retitled, {len(touched)} casts rebuilt")
    print(f"  undo with the mapping in {path}")

if __name__ == "__main__":
    asyncio.run(main())
