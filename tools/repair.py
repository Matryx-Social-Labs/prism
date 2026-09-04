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
  uv run python -m tools.repair --markup        # report only
  uv run python -m tools.repair --reembed       # re-embed the corpus (model swap)
  uv run python -m tools.repair --drop-cve      # remove the CVE-feed corpus
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
import time
import uuid

import asyncpg

from common.embeddings import embed_texts
from common.entity_aliases import ENTITY_ALIASES
from common.text import chunk_text, entity_slug
from enrichment.fulltext import _markup_leaked, retrieve_fulltext

OVER_MERGE_MIN = 20  # members at or above which an event is worth re-deciding
# Modest on purpose: this walks one publisher's site to recover an error we caused,
# and there is no deadline. Being impolite about that is a bad trade.
MARKUP_FETCH_CONCURRENCY = 6


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


# Cluster re-decision used to live here, as a Python reimplementation of the
# match cascade. It drifted from the real matcher FOUR times — omitting the title
# path, omitting the single-actor near band, keeping a stale copy of the top-IDF
# rule, and disagreeing outright (52 -> 7 where the matcher gives 52 -> 13). Each
# drift proposed destroying a legitimate story.
#
# It is deleted rather than fixed. tools/scratch.py replays through
# correlation.clustering.find_event itself, so it cannot drift, and it emits a
# plan this module no longer needs to second-guess:
#
#   uv run python -m tools.scratch --plan out.json
#   uv run python -m tools.scratch --apply-plan out.json --rehearse
#
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
    # raw_items.title is the SOURCE. Fixing only the derived copies is why this
    # defect came back: 119 raw_items still carried escapes from before the
    # clean_text choke point existed, and the 0.0.81.16 repair copied one straight
    # into a new event's title on 2026-08-02 — `INSERT INTO events ... SELECT
    # ri.title` in tools/scratch.py takes it verbatim. Clean the source and every
    # future copy is clean; clean only the copies and the next repair reintroduces it.
    for table, col in (
        ("raw_items", "title"),
        ("events", "title"),
        ("events", "summary"),
        ("stories", "label"),
    ):
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


async def apply_entities(c: asyncpg.Connection, *, write: bool) -> None:
    """Strip outlet names from the graph, and fold the curated alias variants.

    An outlet is not an actor in its own coverage. The forward-only filter added in
    0.0.79.1 stops NEW ones, but the historical links remained — and the cast
    rebuild in tools/scratch.py made it worse, because it read entities straight
    out of shared_fields and never applied that filter. `prajavani` went from part
    of a 345-link problem to 240 links on its own.
    """
    src = {entity_slug(r["slug"]) for r in await c.fetch("SELECT slug FROM sources")}
    src |= {entity_slug(r["name"]) for r in await c.fetch("SELECT name FROM sources")}
    ids = [r["id"] for r in await c.fetch(
        "SELECT id FROM entities WHERE slug = ANY($1::text[])", sorted(src))]
    ev = await c.fetchval("SELECT count(*) FROM event_entities WHERE entity_id = ANY($1::uuid[])", ids)
    ar = await c.fetchval("SELECT count(*) FROM article_entities WHERE entity_id = ANY($1::uuid[])", ids)
    print(f"\n  outlet entities: {len(ids)}   event links: {ev}   article links: {ar}")

    pairs = [(v, k) for k, v in ENTITY_ALIASES.items()]
    folds = 0
    for _canonical, variant in pairs:
        n = await c.fetchval("""SELECT count(*) FROM event_entities ee
              JOIN entities e ON e.id = ee.entity_id WHERE e.slug = $1""", variant)
        folds += n
    print(f"  alias variants to fold: {len(pairs)} slugs, {folds} event links")
    if not write:
        print("  (dry run — nothing written)")
        return

    async with c.transaction():
        await c.execute("DELETE FROM article_entities WHERE entity_id = ANY($1::uuid[])", ids)
        await c.execute("DELETE FROM event_entities WHERE entity_id = ANY($1::uuid[])", ids)
        for canonical, variant in pairs:
            cid = await c.fetchval("SELECT id FROM entities WHERE slug = $1", canonical)
            vid = await c.fetchval("SELECT id FROM entities WHERE slug = $1", variant)
            if not cid or not vid:
                continue
            # Re-point the variant's links at the canonical, then drop the variant.
            for tbl, key in (("event_entities", "event_id"), ("article_entities", "article_id")):
                await c.execute(
                    f"""UPDATE {tbl} SET entity_id = $1 WHERE entity_id = $2
                        AND NOT EXISTS (SELECT 1 FROM {tbl} t2
                                        WHERE t2.{key} = {tbl}.{key} AND t2.entity_id = $1)""",
                    cid, vid)
                await c.execute(f"DELETE FROM {tbl} WHERE entity_id = $1", vid)
            await c.execute("UPDATE impacts SET entity_id = $1 WHERE entity_id = $2", cid, vid)
            # The variant entity ROW is left in place. impacts is not the only
            # thing that can reference it, and chasing every foreign key to delete
            # a row nobody reads is work for its own sake — entity_slug already
            # resolves new mentions to the canonical, so nothing links here again.
    print(f"  APPLIED: {ev + ar} outlet links removed, {len(pairs)} alias variants folded")


async def report_markup(c: asyncpg.Connection, limit: int | None = None) -> list[dict]:
    """Articles whose clean_text came back as MARKUP, refetched through the fixed path.

    Sibling of report_titles: that one unescapes HTML ENTITIES in a title, this one
    removes HTML TAGS from an article body. 877 rows, 854 of them one source, where
    trafilatura returned the page's HTML as if it were text.

    NO LLM CREDITS. The obvious repair — re-run enrichment — is not needed, because
    the extraction is fine: the affected source averages 9.30 entities per article
    against 7.54 for a clean Kannada control, all 883 of its enrichments have a
    summary, and the summaries are specific and correct. The model read straight
    through the markup. What is actually damaged is the TEXT and the vectors built
    from it — `clean_text` is the string a claim's quote is verified against, and
    `article_chunks.embedding` currently encodes "</p>" and an App Store link. Both
    are repaired by refetching and re-embedding: HTTP plus local ONNX, cost zero.
    """
    print(f"\n{'='*74}\nCLEAN_TEXT holding HTML tags\n{'='*74}")
    rows = [dict(r) for r in await c.fetch(
        """
        SELECT a.id::text AS id, ri.url AS url, length(a.clean_text) AS chars, s.slug AS src
        FROM articles a
        JOIN raw_items ri ON ri.id = a.raw_item_id
        JOIN sources s ON s.id = ri.source_id
        WHERE a.clean_text ~ '</[a-zA-Z]+>' AND ri.url IS NOT NULL
        ORDER BY a.created_at
        """
    )]
    if limit:
        rows = rows[:limit]
        print(f"\n  --limit {limit}: smoke test on the first {len(rows)}")
    by_src: dict[str, int] = {}
    for r in rows:
        by_src[r["src"]] = by_src.get(r["src"], 0) + 1
    print(f"\n  {len(rows)} articles, by source:")
    for slug, n in sorted(by_src.items(), key=lambda kv: -kv[1]):
        print(f"    {n:>5}  {slug}")

    sem = asyncio.Semaphore(MARKUP_FETCH_CONCURRENCY)

    async def one(r: dict) -> dict:
        async with sem:
            try:
                text, _tier, _img = await retrieve_fulltext(r["url"], None)
            except Exception as exc:
                return {**r, "skip": f"fetch failed ({type(exc).__name__})"}
        if not text:
            # NEVER blank a row. Contaminated text is worse than clean text and far
            # better than none: emptying clean_text would delete an article's whole
            # evidence trail in order to fix its formatting.
            return {**r, "skip": "empty result"}
        if _markup_leaked(text):
            return {**r, "skip": "still markup after refetch"}
        return {**r, "text": text}

    out = await asyncio.gather(*(one(r) for r in rows))
    fixed = [r for r in out if "text" in r]
    skipped = [r for r in out if "skip" in r]
    print(f"\n  refetched clean : {len(fixed)}")
    print(f"  left untouched  : {len(skipped)}")
    for reason in sorted({r["skip"] for r in skipped}):
        print(f"      {sum(1 for r in skipped if r['skip'] == reason):>4}  {reason}")
    if fixed:
        was, now = sum(r["chars"] for r in fixed), sum(len(r["text"]) for r in fixed)
        print(f"  chars {was:,} -> {now:,}  ({100 * (was - now) // max(was, 1)}% of it was markup)")
        print(f"\n  sample: {fixed[0]['text'][:110]!r}")
    return fixed


async def apply_markup(c: asyncpg.Connection, fixed: list[dict]) -> None:
    """Write the refetched text and rebuild each article's chunks.

    Embeddings are computed BEFORE the transaction opens: they are pure local
    compute and holding a production write transaction across minutes of ONNX for
    no reason is how a repair becomes an incident.
    """
    prepared = []
    for r in fixed:
        chunks = chunk_text(r["text"])
        prepared.append((r["id"], r["text"], chunks, await embed_texts(chunks)))

    async with c.transaction():
        for aid, text, chunks, vecs in prepared:
            await c.execute(
                "UPDATE articles SET clean_text = $2, word_count = $3 WHERE id = $1::uuid",
                aid, text, len(text.split()),
            )
            # Replaced, not updated in place: the clean text may chunk into a
            # DIFFERENT number of pieces, and updating would leave orphaned tail
            # chunks still holding the markup.
            await c.execute("DELETE FROM article_chunks WHERE article_id = $1::uuid", aid)
            for idx, (chunk, vec) in enumerate(zip(chunks, vecs, strict=True)):
                # `id` is supplied explicitly. ArticleChunk.id is a PYTHON-side
                # default (uuid_pk in common/models.py), not a database one, so a
                # raw INSERT that omits it hits a NOT NULL violation — which is
                # exactly what the first run of this did. The transaction rolled
                # it back cleanly; the lesson is that bypassing the ORM means
                # bypassing its defaults too.
                await c.execute(
                    "INSERT INTO article_chunks (id, article_id, chunk_index, text, embedding) "
                    "VALUES ($1::uuid, $2::uuid, $3, $4, $5::vector)",
                    str(uuid.uuid4()), aid, idx, chunk,
                    "[" + ",".join(f"{v:.6f}" for v in vec) + "]",
                )
    left = await c.fetchval("SELECT count(*) FROM articles WHERE clean_text ~ '</[a-zA-Z]+>'")
    print(f"  APPLIED: {len(prepared)} articles rewritten and re-embedded")
    print(f"  articles still holding markup: {left}")
    # events.embedding is copied from an article's first chunk at event creation
    # (correlation/consumer._first_chunk_embedding), so events founded by one of
    # these articles still carry a vector built from markup. Rewriting those would
    # change the embedding kNN edges the v2 story layer is built from — a change to
    # the story graph, unmeasured. Left for a partition replay to decide.
    print("  NOTE: events.embedding is NOT rewritten — see the comment in apply_markup.")


async def reembed(c: asyncpg.Connection, *, write: bool, batch: int = 256) -> None:
    """Rebuild every stored vector with the CONFIGURED model, then record it.

    Needed because cosine distance is not comparable across embedding models. A
    config change alone leaves the database full of the old model's vectors and
    the new model's queries scoring against them — measured at 25x the false
    merges, with nothing logged. So the order is always: re-embed first, deploy
    the config second.

    Local ONNX only. No LLM, no spend, just time.

    Event vectors are recomputed from each event's FIRST-CHUNK article, which is
    where correlation/consumer._first_chunk_embedding took them originally. That
    also repairs the ~1,100 events still holding a vector built from the markup
    this file's --markup section cleaned out of clean_text.
    """
    from common.config import get_settings
    from common.embeddings import DOC_PREFIX, _needs_prefix, embed_texts

    settings = get_settings()
    model, dim = settings.prism_embed_model, settings.prism_embed_dim
    prefix = DOC_PREFIX if _needs_prefix(model) else None
    print(f"\n{'='*74}\nRE-EMBED corpus with {model}\n{'='*74}")
    print(f"  dim {dim}   document prefix {prefix!r}")

    try:
        current = await c.fetchrow(
            "SELECT embed_model, embed_prefix FROM corpus_meta WHERE id = 1"
        )
        has_meta = True
    except asyncpg.exceptions.UndefinedTableError:
        # The guard's table ships in a migration that may not be deployed yet.
        # That must not block the re-embed: the vectors are the thing that takes
        # time, and the migration seeds the record from settings when it does run,
        # which is correct precisely BECAUSE the re-embed went first.
        current, has_meta = None, False
    print(f"  corpus currently: {dict(current) if current else 'unknown (corpus_meta not deployed)'}")

    n_chunks = await c.fetchval("SELECT count(*) FROM article_chunks")
    n_events = await c.fetchval("SELECT count(*) FROM events WHERE embedding IS NOT NULL")
    print(f"  {n_chunks} chunks and {n_events} event vectors would be rewritten")
    if not write:
        print("\n  DRY RUN — nothing written.")
        return

    # KEYSET pagination and BATCHED writes. Both were measured before changing:
    #   embed, 4 threads       99 ms/chunk    ->  1.3 h      (raised to 8: 0.7 h)
    #   one UPDATE per row    182 ms round trip -> 2.4 h     <- the real ceiling
    #   OFFSET 40000 vs keyset 0.61s vs 0.47s  ->  negligible
    # So the round trips were the thing to fix, not the OFFSET I first suspected.
    done, last = 0, "00000000-0000-0000-0000-000000000000"
    t0 = time.perf_counter()
    while True:
        rows = await c.fetch(
            "SELECT id::text AS id, text FROM article_chunks "
            "WHERE id > $1::uuid ORDER BY id LIMIT $2",
            last, batch,
        )
        if not rows:
            break
        vecs = await embed_texts([r["text"] for r in rows])
        await c.executemany(
            "UPDATE article_chunks SET embedding = $2::vector WHERE id = $1::uuid",
            [(r["id"], "[" + ",".join(f"{x:.6f}" for x in v) + "]")
             for r, v in zip(rows, vecs, strict=True)],
        )
        done += len(rows)
        last = rows[-1]["id"]
        if done % (batch * 8) == 0:
            rate = done / max(time.perf_counter() - t0, 1e-9)
            left = (n_chunks - done) / max(rate, 1e-9) / 60
            print(f"    chunks {done}/{n_chunks}  {rate:.0f}/s  ~{left:.0f} min left", flush=True)
    print(f"  chunks rewritten: {done} in {(time.perf_counter()-t0)/60:.1f} min")

    # Events take their vector from the first chunk of their earliest article,
    # matching how correlation assigned it in the first place.
    await c.execute(
        """
        WITH first_chunk AS (
            SELECT DISTINCT ON (em.event_id) em.event_id, ac.embedding
            FROM event_memberships em
            JOIN articles a ON a.id = em.article_id
            JOIN article_chunks ac ON ac.article_id = a.id AND ac.chunk_index = 0
            ORDER BY em.event_id, a.created_at, a.id
        )
        UPDATE events e SET embedding = f.embedding
        FROM first_chunk f
        WHERE e.id = f.event_id AND e.embedding IS NOT NULL
        RETURNING 1
        """
    )
    n_moved = await c.fetchval("SELECT count(*) FROM events WHERE embedding IS NOT NULL")
    print(f"  event vectors rebuilt from their first chunk (now {n_moved} non-null)")

    if has_meta:
        await c.execute(
            "UPDATE corpus_meta SET embed_model = $1, embed_dim = $2, embed_prefix = $3, "
            "updated_at = now() WHERE id = 1",
            model, dim, prefix,
        )
        print(f"  corpus_meta now records {model} / {prefix!r}")
    else:
        print(f"  corpus_meta absent — the migration will seed {model} / {prefix!r} on deploy,")
        print("  which is correct because the vectors were rewritten first.")
    print("  Deploy the matching config AFTER this, never before.")


# Every table that points at articles / raw_items / events, in the order the
# foreign keys allow. Read out of information_schema rather than remembered:
# guessing this order is how a delete half-completes and rolls back after an hour.
_CVE_ARTICLE_CHILDREN = ("article_chunks", "article_entities", "event_memberships")
_CVE_EVENT_CHILDREN = (
    "event_entities", "event_story", "impacts", "perspectives", "agent_sessions",
)


async def drop_cve(c: asyncpg.Connection, *, write: bool) -> None:
    """Delete the CVE-feed corpus: NVD and CISA KEV.

    19,276 articles, 77% of all events, ingested during the cyber beachhead and
    not wanted for the India news product as it stands.

    SAFE TO DELETE IN THE SENSE THAT MATTERS: both are public authoritative feeds
    and their enrichment is DETERMINISTIC (enrichment/cve_lens.extract_from_nvd —
    no LLM), so the whole set is reconstructible for free by re-enabling the
    collectors. This is not discarding paid-for work.

    Events are only removed when nothing is left in them. 30 events mix CVE and
    news members; those keep their news members and lose the CVE ones, because
    deleting the event would take real reporting with it.
    """
    print(f"\n{'='*74}\nDROP the CVE-feed corpus (nvd + cisa_kev)\n{'='*74}")
    where = "s.source_type = 'cve_feed'"
    # KEEP anything a labelling task still points at. Five tasks in the completed
    # story-boundary batch use CVE events as seeds or candidates, and that batch
    # holds 252 human answers — deleting the events would make the gold set
    # impossible to re-compile from its source, to save five rows out of 19,276.
    labelled = """SELECT em.article_id FROM event_memberships em
                  WHERE em.event_id IN (SELECT seed_event_id FROM label_tasks
                                        WHERE seed_event_id IS NOT NULL)"""
    art = f"""SELECT a.id FROM articles a JOIN raw_items ri ON ri.id = a.raw_item_id
              JOIN sources s ON s.id = ri.source_id
              WHERE {where} AND a.id NOT IN ({labelled})"""
    raw = f"""SELECT ri.id FROM raw_items ri JOIN sources s ON s.id = ri.source_id
              WHERE {where} AND ri.id NOT IN (SELECT raw_item_id FROM articles
                                              WHERE id IN ({labelled}))"""

    n_art = await c.fetchval(f"SELECT count(*) FROM ({art}) t")
    n_raw = await c.fetchval(f"SELECT count(*) FROM ({raw}) t")
    cve_only = await c.fetchval("""
        SELECT count(*) FROM events e
        WHERE EXISTS (SELECT 1 FROM event_memberships em WHERE em.event_id = e.id)
          AND NOT EXISTS (
            SELECT 1 FROM event_memberships em JOIN articles a ON a.id = em.article_id
            JOIN raw_items ri ON ri.id = a.raw_item_id JOIN sources s ON s.id = ri.source_id
            WHERE em.event_id = e.id AND s.source_type <> 'cve_feed')""")
    print(f"  articles {n_art}   raw_items {n_raw}   events that would empty out {cve_only}")

    kept = await c.fetchval(f"""
        SELECT count(*) FROM articles a JOIN raw_items ri ON ri.id = a.raw_item_id
        JOIN sources s ON s.id = ri.source_id
        WHERE {where} AND a.id IN ({labelled})""")
    print(f"  keeping {kept} CVE articles that a labelling task still references")

    # Belt and braces: after the exclusion, nothing a task points at may vanish.
    pinned = await c.fetchval(f"""
        SELECT count(*) FROM label_tasks lt WHERE lt.seed_event_id IN (
          SELECT em.event_id FROM event_memberships em WHERE em.article_id IN ({art}))""")
    if pinned:
        print(f"  REFUSING: {pinned} label_tasks would still lose their event")
        return

    if not write:
        print("\n  DRY RUN — nothing deleted.")
        return

    async with c.transaction():
        await c.execute(f"DELETE FROM field_provenance WHERE enrichment_id IN "
                        f"(SELECT id FROM enrichments WHERE article_id IN ({art}))")
        await c.execute(f"DELETE FROM enrichments WHERE article_id IN ({art})")
        for t in _CVE_ARTICLE_CHILDREN:
            await c.execute(f"DELETE FROM {t} WHERE article_id IN ({art})")
        await c.execute(f"DELETE FROM articles WHERE id IN ({art})")
        await c.execute(f"DELETE FROM raw_items WHERE id IN ({raw})")
        # Now the orphans: events whose every member has just gone.
        orphan = """SELECT e.id FROM events e WHERE NOT EXISTS
                    (SELECT 1 FROM event_memberships em WHERE em.event_id = e.id)"""
        await c.execute(f"DELETE FROM event_links WHERE from_event_id IN ({orphan}) "
                        f"OR to_event_id IN ({orphan})")
        for t in _CVE_EVENT_CHILDREN:
            await c.execute(f"DELETE FROM {t} WHERE event_id IN ({orphan})")
        gone = await c.fetchval(f"WITH d AS (DELETE FROM events WHERE id IN ({orphan}) "
                                f"RETURNING 1) SELECT count(*) FROM d")
    print(f"  deleted. events removed: {gone}")
    for t in ("raw_items", "articles", "article_chunks", "enrichments", "events"):
        print(f"    {t:16} now {await c.fetchval(f'SELECT count(*) FROM {t}')}")


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--entities", action="store_true")
    ap.add_argument("--titles", action="store_true")
    ap.add_argument("--markup", action="store_true", help="clean_text holding HTML tags")
    ap.add_argument("--drop-cve", action="store_true",
                    help="delete the NVD/CISA-KEV corpus (reconstructible: public feeds, "
                         "deterministic enrichment, no LLM cost)")
    ap.add_argument("--reembed", action="store_true",
                    help="rebuild every vector with the configured model (local, free)")
    ap.add_argument("--limit", type=int, default=None,
                    help="cap articles for --markup; prove the write path on a few first")
    ap.add_argument("--apply", action="store_true", help="WRITE. Without it, nothing changes.")
    a = ap.parse_args()
    every = not (a.entities or a.titles or a.markup or a.reembed or a.drop_cve)

    c = await asyncpg.connect(_db_url(), timeout=45)
    try:
        if not a.apply:
            # Belt and braces: the server refuses writes even if the code is wrong.
            await c.execute("SET default_transaction_read_only = on")
            print("DRY RUN — the connection is read-only, nothing can be written.")
        else:
            print("!! APPLY MODE — this will write to production.")

        if every or a.entities:
            await report_entities(c)
            await apply_entities(c, write=a.apply and a.entities)
        if every or a.titles:
            fixes = await report_titles(c)
            if a.apply and a.titles:
                await apply_titles(c, fixes)
        if a.drop_cve:
            await drop_cve(c, write=a.apply and a.drop_cve)
        if a.reembed:
            await reembed(c, write=a.apply and a.reembed)
        if every or a.markup:
            fixed = await report_markup(c, a.limit)
            if a.apply and a.markup:
                await apply_markup(c, fixed)

        if not a.apply:
            print("\nNothing was written. Re-run with --apply plus a section to act.")
    finally:
        await c.close()


if __name__ == "__main__":
    asyncio.run(main())
