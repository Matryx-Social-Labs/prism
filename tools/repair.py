"""Repair data that was written before the clustering and canonicalisation fixes.

Every fix in v0.0.79-80 is FORWARD-ONLY: it changes what gets written from now on
and leaves history alone. So production still serves a 139-article Kannada
over-merge, outlet names as cast members, source counts inflated by syndication,
and titles carrying HTML entities. This repairs that.

DRY RUN IS THE DEFAULT. Nothing writes without --apply, and --apply is refused
unless you also pass the section you mean. The cluster rebuild is destructive —
it deletes and rewrites event_memberships — so read its report before trusting it.

  uv run python -m tools.repair                 # report everything, write nothing
  uv run python -m tools.repair --titles --apply
  uv run python -m tools.repair --clusters      # report only

The expensive work is already paid for: extraction and embeddings exist on every
one of these rows. Re-deciding who belongs with whom is pure computation over data
we hold, so none of this needs LLM credits.
"""

from __future__ import annotations

import argparse
import asyncio
import html as _html
import json
import os
import re
import subprocess

import asyncpg

from common.entity_aliases import ENTITY_ALIASES
from common.text import detect_script, entity_slug
from correlation.clustering import (
    EMBEDDING_DISTANCE_THRESHOLD,
    EMBEDDING_TRUSTED_SCRIPTS,
    ENTITY_MATCH_LOOSE_DISTANCE,
    ENTITY_MATCH_MIN_IDF,
    ENTITY_MATCH_MIN_SHARED,
    ENTITY_MATCH_MIN_TOP_IDF,
    ENTITY_MATCH_NEAR_DISTANCE,
    ENTITY_MATCH_TYPES,
    TITLE_SIMILARITY_THRESHOLD,
)

OVER_MERGE_MIN = 20  # members at or above which an event is worth re-deciding


def _db_url() -> str:
    """Prefer an explicit URL; otherwise ask Railway for the public proxy."""
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
        raise SystemExit("no database url (set REPAIR_DATABASE_URL)")
    return re.sub(r"^postgresql\+asyncpg://", "postgresql://", raw)


def _json(v):
    return json.loads(v) if isinstance(v, str) else v


def _cos(a: list[float], b: list[float]) -> float:
    """Cosine DISTANCE, matching pgvector's <=>."""
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    return 1.0 - dot / (na * nb) if na and nb else 1.0


# ── section 1: re-decide the over-merged clusters ───────────────────────────

def _actors(entities: list[dict]) -> set[str]:
    """Countable actor slugs for an article — the same filter the gate applies."""
    return {
        entity_slug(e["name"])
        for e in (entities or [])
        if e.get("name") and e.get("type") in ENTITY_MATCH_TYPES
    }


def _rebuild(members: list[dict], df: dict[str, float], sim: dict[tuple, float] | None = None) -> list[list[dict]]:
    """Replay the CURRENT matching rules over one event's members, in arrival order.

    A faithful replay rather than a re-run of find_event: the members are compared
    only against each other, which is what re-deciding a single event means. Each
    cluster is represented by its founding article's embedding, mirroring the way
    an event carries one vector.
    """
    clusters: list[dict] = []
    for m in sorted(members, key=lambda x: (x["published_at"] or x["created_at"], str(x["aid"]))):
        script = detect_script(m["title"] or "")
        trusted = script in EMBEDDING_TRUSTED_SCRIPTS
        placed = False
        for c in clusters:
            dist = _cos(m["vec"], c["vec"])
            founder = c["members"][0]["aid"]
            # title path FIRST, exactly as the cascade orders it. Omitting this
            # was the bug the canary caught: three articles about the same
            # Supreme Court hearing had matched on trigram title similarity, and
            # a replay without it proposed splitting them into singletons —
            # destroying real corroboration in the name of repairing it.
            if sim is not None and sim.get((m["aid"], founder), 0.0) >= TITLE_SIMILARITY_THRESHOLD:
                placed = True
            # embedding path — only where the model's subspace isn't collapsed
            elif trusted and dist <= EMBEDDING_DISTANCE_THRESHOLD:
                placed = True
            else:
                # actor path: >=2 shared, IDF-weighted, one individually specific,
                # and the single-actor near-band shortcut off for collapsed scripts
                shared = m["actors"] & c["actors"]
                # >=2 shared actors normally; ONE is enough inside the near-dup
                # band, but only for a trusted script — for a collapsed one that
                # band spans most unrelated pairs, which is what let 18 articles
                # into the Kannada hairball. Omitting this branch entirely was the
                # canary's second finding: it made the replay STRICTER than
                # production and proposed splitting three articles that had
                # legitimately joined at distances 0.23-0.36.
                need = (
                    1 if (trusted and dist <= ENTITY_MATCH_NEAR_DISTANCE)
                    else ENTITY_MATCH_MIN_SHARED
                )
                if (
                    dist <= ENTITY_MATCH_LOOSE_DISTANCE
                    and len(shared) >= need
                    and sum(1.0 / df.get(s, 1.0) for s in shared) >= ENTITY_MATCH_MIN_IDF
                    and max((1.0 / df.get(s, 1.0) for s in shared), default=0) >= ENTITY_MATCH_MIN_TOP_IDF
                ):
                    placed = True
            if placed:
                c["members"].append(m)
                c["actors"] |= m["actors"]
                break
        if not placed:
            clusters.append({"vec": m["vec"], "actors": set(m["actors"]), "members": [m]})
    return [c["members"] for c in clusters]


async def report_clusters(c: asyncpg.Connection) -> None:
    rows = await c.fetch(
        """SELECT em.event_id, count(*) n FROM event_memberships em
           GROUP BY em.event_id HAVING count(*) >= $1 ORDER BY n DESC""",
        OVER_MERGE_MIN,
    )
    print(f"\n{'='*74}\nCLUSTERS — {len(rows)} events at or above {OVER_MERGE_MIN} members\n{'='*74}")

    df: dict[str, float] = {}
    for r in await c.fetch(
        """SELECT ent.slug, count(DISTINCT ee.event_id)::float d
           FROM entities ent JOIN event_entities ee ON ee.entity_id = ent.id
           WHERE ent.entity_type = ANY($1::text[]) GROUP BY ent.slug""",
        list(ENTITY_MATCH_TYPES),
    ):
        df[r["slug"]] = r["d"]

    total_before = total_after = 0
    for r in rows:
        members = []
        for m in await c.fetch(
            """SELECT a.id aid, ri.title, ri.published_at, a.created_at,
                      ac.embedding::text vec, e.shared_fields->'entities' ents
               FROM event_memberships em
               JOIN articles a ON a.id = em.article_id
               JOIN raw_items ri ON ri.id = a.raw_item_id
               JOIN article_chunks ac ON ac.article_id = a.id AND ac.chunk_index = 0
               LEFT JOIN enrichments e ON e.article_id = a.id
               WHERE em.event_id = $1""",
            r["event_id"],
        ):
            members.append({
                "aid": m["aid"], "title": m["title"],
                "published_at": m["published_at"], "created_at": m["created_at"],
                "vec": [float(x) for x in m["vec"].strip("[]").split(",")],
                "actors": _actors(_json(m["ents"]) or []),
            })
        sim = await _title_sim(c, members)
        out = _rebuild(members, df, sim)
        sizes = sorted((len(x) for x in out), reverse=True)
        total_before += len(members)
        total_after += len(out)
        scripts = {detect_script(m["title"] or "") for m in members}
        head = (members[0]["title"] or "")[:52]
        print(f"\n  {r['event_id']}  {len(members)} -> {len(out)} clusters   scripts={sorted(scripts)}")
        print(f"    sizes: {sizes[:12]}{' ...' if len(sizes) > 12 else ''}")
        print(f"    was:   {head}")
    print(f"\n  TOTAL: {total_before} articles in {len(rows)} events -> {total_after} events")


# ── section 2: entity graph ─────────────────────────────────────────────────

async def report_entities(c: asyncpg.Connection) -> None:
    print(f"\n{'='*74}\nENTITIES\n{'='*74}")
    src = {entity_slug(r["slug"]) for r in await c.fetch("SELECT slug FROM sources")}
    src |= {entity_slug(r["name"]) for r in await c.fetch("SELECT name FROM sources")}
    outlets = await c.fetch(
        """SELECT e.id, e.slug, count(ee.id) links FROM entities e
           LEFT JOIN event_entities ee ON ee.entity_id = e.id
           WHERE e.slug = ANY($1::text[]) GROUP BY e.id, e.slug ORDER BY links DESC""",
        sorted(src),
    )
    print(f"\n  outlets currently in the graph: {len(outlets)}")
    for o in outlets[:10]:
        print(f"    {o['slug']:28} {o['links']} event links")

    print("\n  alias pairs that would fold:")
    for variant, canonical in sorted(ENTITY_ALIASES.items()):
        got = await c.fetch(
            """SELECT e.slug, count(ee.id) links FROM entities e
               LEFT JOIN event_entities ee ON ee.entity_id = e.id
               WHERE e.slug = ANY($1::text[]) GROUP BY e.slug""",
            [variant, canonical],
        )
        if len(got) == 2:
            d = {g["slug"]: g["links"] for g in got}
            print(f"    {variant:28} ({d.get(variant,0)} links) -> {canonical} ({d.get(canonical,0)})")


# ── section 3: titles written before the clean_text choke point ─────────────

_ENTITY_RE = re.compile(r"&(?:amp|quot|nbsp|lt|gt|#0?39|#x27|#8217|#\d+);", re.I)


async def report_titles(c: asyncpg.Connection) -> list[tuple]:
    print(f"\n{'='*74}\nTITLES / SUMMARIES with HTML entities\n{'='*74}")
    fixes = []
    for table, col in (("events", "title"), ("events", "summary"), ("stories", "label")):
        rows = await c.fetch(
            f"SELECT id, {col} v FROM {table} WHERE {col} ~ '&(amp|quot|nbsp|lt|gt|#[0-9a-fA-F]+);'"
        )
        print(f"\n  {table}.{col}: {len(rows)} rows")
        for r in rows[:4]:
            fixed = _html.unescape(r["v"])
            print(f"    - {r['v'][:64]}")
            print(f"      -> {fixed[:64]}")
        for r in rows:
            fixed = _html.unescape(r["v"])
            if fixed != r["v"]:
                fixes.append((table, col, r["id"], fixed))
    print(f"\n  total rows that would change: {len(fixes)}")
    return fixes


async def apply_titles(c: asyncpg.Connection, fixes: list[tuple]) -> None:
    for table, col, rid, fixed in fixes:
        await c.execute(f"UPDATE {table} SET {col} = $1 WHERE id = $2", fixed, rid)
    print(f"  APPLIED: {len(fixes)} rows unescaped")


async def split_event(c: asyncpg.Connection, event_id, *, apply: bool) -> None:
    """Re-decide ONE over-merged event and, with --apply, split it for real.

    The biggest cluster keeps the original event id, so the story readers already
    have a link to stays where it is; the rest become new events. Everything runs
    in one transaction and writes a rollback file first, because this is the only
    destructive repair here — memberships move, and an event that never should
    have existed is easier to create than to un-create.

    The new events carry title, summary, embedding, sector and regions from their
    own founding article, plus entities derived from their members' existing
    extractions. They will have no lens brief until the analyser next runs, which
    the UI already renders honestly ("No reader reading of this story yet").
    """
    members, df = await _members_of(c, event_id), await _df(c)
    sim = await _title_sim(c, members)
    clusters = sorted(_rebuild(members, df, sim), key=len, reverse=True)
    print(f"\n  {event_id}: {len(members)} members -> {len(clusters)} clusters")
    for i, cl in enumerate(clusters):
        tag = "KEEPS the original event id" if i == 0 else "new event"
        print(f"    [{len(cl):>3}] {tag:28} {(cl[0]['title'] or '')[:44]}")
    if not apply:
        print("  (dry run — nothing written)")
        return

    rollback = {
        "event_id": str(event_id),
        "memberships": [{"article_id": str(m["aid"])} for m in members],
    }
    path = f"/tmp/repair-rollback-{event_id}.json"
    with open(path, "w") as fh:
        json.dump(rollback, fh, indent=2)
    print(f"  rollback written: {path}")

    async with c.transaction():
        for cl in clusters[1:]:
            founder = cl[0]
            new_id = await c.fetchval(
                """INSERT INTO events (id, title, summary, sector, subsector, regions,
                                       occurred_at, embedding, last_updated_at)
                   SELECT gen_random_uuid(), ri.title, e.summary, ev.sector, ev.subsector,
                          ev.regions, e.occurred_at, ac.embedding, now()
                   FROM articles a
                   JOIN raw_items ri ON ri.id = a.raw_item_id
                   JOIN article_chunks ac ON ac.article_id = a.id AND ac.chunk_index = 0
                   LEFT JOIN enrichments e ON e.article_id = a.id
                   CROSS JOIN (SELECT sector, subsector, regions FROM events WHERE id = $2) ev
                   WHERE a.id = $1
                   RETURNING id""",
                founder["aid"], event_id,
            )
            await c.execute(
                """UPDATE event_memberships SET event_id = $1
                   WHERE event_id = $2 AND article_id = ANY($3::uuid[])""",
                new_id, event_id, [m["aid"] for m in cl],
            )
            # Actors for the new event, from extractions we already hold.
            slugs = sorted({s for m in cl for s in m["actors"]})
            if slugs:
                await c.execute(
                    """INSERT INTO event_entities (id, event_id, entity_id, role)
                       SELECT gen_random_uuid(), $1, ent.id, 'subject'
                       FROM entities ent WHERE ent.slug = ANY($2::text[])
                       ON CONFLICT DO NOTHING""",
                    new_id, slugs,
                )
        # The original event's own actor links now over-state it; rebuild from
        # the members it kept rather than leaving inherited ones behind.
        kept = sorted({s for m in clusters[0] for s in m["actors"]})
        await c.execute("DELETE FROM event_entities WHERE event_id = $1", event_id)
        if kept:
            await c.execute(
                """INSERT INTO event_entities (id, event_id, entity_id, role)
                   SELECT gen_random_uuid(), $1, ent.id, 'subject'
                   FROM entities ent WHERE ent.slug = ANY($2::text[])
                   ON CONFLICT DO NOTHING""",
                event_id, kept,
            )
    print(f"  APPLIED: {len(clusters) - 1} new events created, {len(members)} memberships re-homed")


async def _df(c: asyncpg.Connection) -> dict[str, float]:
    return {
        r["slug"]: r["d"]
        for r in await c.fetch(
            """SELECT ent.slug, count(DISTINCT ee.event_id)::float d
               FROM entities ent JOIN event_entities ee ON ee.entity_id = ent.id
               WHERE ent.entity_type = ANY($1::text[]) GROUP BY ent.slug""",
            list(ENTITY_MATCH_TYPES),
        )
    }


async def _title_sim(c: asyncpg.Connection, members: list[dict]) -> dict[tuple, float]:
    """pg_trgm similarity for every member pair, computed BY POSTGRES.

    Reimplementing trigram similarity in Python would be a second source of truth
    for the thing being repaired; asking the same function the matcher asks keeps
    the replay honest.
    """
    ids = [m["aid"] for m in members]
    titles = [m["title"] or "" for m in members]
    out: dict[tuple, float] = {}
    for r in await c.fetch(
        """SELECT a.id ai, b.id bi, similarity(a.t, b.t) s
           FROM unnest($1::uuid[], $2::text[]) AS a(id, t)
           CROSS JOIN unnest($1::uuid[], $2::text[]) AS b(id, t)
           WHERE a.id <> b.id AND similarity(a.t, b.t) >= $3""",
        ids, titles, TITLE_SIMILARITY_THRESHOLD,
    ):
        out[(r["ai"], r["bi"])] = r["s"]
    return out


async def _members_of(c: asyncpg.Connection, event_id) -> list[dict]:
    out = []
    for m in await c.fetch(
        """SELECT a.id aid, ri.title, ri.published_at, a.created_at,
                  ac.embedding::text vec, e.shared_fields->'entities' ents
           FROM event_memberships em
           JOIN articles a ON a.id = em.article_id
           JOIN raw_items ri ON ri.id = a.raw_item_id
           JOIN article_chunks ac ON ac.article_id = a.id AND ac.chunk_index = 0
           LEFT JOIN enrichments e ON e.article_id = a.id
           WHERE em.event_id = $1""",
        event_id,
    ):
        out.append({
            "aid": m["aid"], "title": m["title"],
            "published_at": m["published_at"], "created_at": m["created_at"],
            "vec": [float(x) for x in m["vec"].strip("[]").split(",")],
            "actors": _actors(_json(m["ents"]) or []),
        })
    return out


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clusters", action="store_true")
    ap.add_argument("--entities", action="store_true")
    ap.add_argument("--titles", action="store_true")
    ap.add_argument("--split", metavar="EVENT_ID", help="re-decide ONE event (canary)")
    ap.add_argument("--apply", action="store_true", help="WRITE. Without it, nothing changes.")
    a = ap.parse_args()
    every = not (a.clusters or a.entities or a.titles or a.split)

    c = await asyncpg.connect(_db_url(), timeout=45)
    try:
        if not a.apply:
            # Belt and braces: the server refuses writes even if the code is wrong.
            await c.execute("SET default_transaction_read_only = on")
            print("DRY RUN — the connection is read-only, nothing can be written.")
        else:
            print("!! APPLY MODE — this will write to production.")

        if a.split:
            import uuid as _uuid
            await split_event(c, _uuid.UUID(a.split), apply=a.apply)
        elif every or a.clusters:
            await report_clusters(c)
        if every or a.entities:
            await report_entities(c)
        if every or a.titles:
            fixes = await report_titles(c)
            if a.apply and a.titles:
                await apply_titles(c, fixes)

        if not a.apply:
            print("\nNothing was written. Re-run with --apply plus a section to act.")
    finally:
        await c.close()


if __name__ == "__main__":
    asyncio.run(main())
