"""Link entity rows to Wikidata QIDs, and measure what that collapses.

The defect: entity identity is a slug, and a slug folds strings. Every
romanisation of a party is its own row until a human adds a line to
common/entity_aliases.py. That is not just untidy — every clustering site weights
actors by 1/df, so a split halves each side's document frequency and makes a
national fixture look twice as distinctive as it is.

Three phases, each independently re-runnable, network work cached in the DB:

  --fetch    ask Wikidata for candidates for our entity names and store every
             surface form they carry (slow, network, idempotent)
  (default)  match entities against the local index and REPORT what would fold
  --write    persist qid/resolution

Writing a qid does NOT repoint any mention. This pass only records identity; the
fold that merges rows is separate and deliberately so, because a repoint is
unrecoverable and a qid is one UPDATE away from being undone.

MATCHING IS EXACT, never fuzzy. Search ranks by fuzzy relevance and top-1 on a
fuzzy rank is how "cjp" becomes an unrelated party — in this corpus that string
also initialises four other organisations. So search is used only to FIND
candidates; the link is an exact normalised match against the candidate's own
surface forms. No match is a fine outcome: the entity keeps its slug.
"""

import argparse
import asyncio
import json
import os
import re
import sys

import asyncpg

from common.entity_aliases import resolve_alias
from common.wikidata import (
    INDIA,
    agent_qids,
    alias_key,
    entity_context,
    fetch_aliases,
    search,
)


def _db_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        env = os.path.join(os.path.dirname(__file__), "..", ".env")
        m = re.search(r"DATABASE_URL=(\S+)", open(env).read())
        url = m.group(1) if m else ""
    return url.replace("postgresql+asyncpg://", "postgresql://").strip()


async def load_entities(c, min_df: int) -> list[dict]:
    """Person/organization entities with their document frequency.

    Restricted to df >= min_df because an entity in ONE event can never form a
    shared-actor edge — it is clustering-inert, so folding it changes nothing that
    is measured. The default of 2 is the set where a fold can actually pay.

    Deliberately does NOT select `qid`: nothing downstream reads it, and leaving it
    out means this runs against a corpus that has not had the migration applied —
    which is the whole point of being able to measure production read-only before
    deciding whether to migrate it.
    """
    return [dict(r) for r in await c.fetch(
        """
        SELECT e.id, e.slug, e.name, count(DISTINCT ee.event_id)::int AS df
        FROM entities e
        JOIN event_entities ee ON ee.entity_id = e.id
        WHERE e.entity_type IN ('person', 'organization')
        GROUP BY e.id, e.slug, e.name
        HAVING count(DISTINCT ee.event_id) >= $1
        ORDER BY count(DISTINCT ee.event_id) DESC
        """,
        min_df,
    )]


async def fetch_index(c, ents: list[dict], limit: int) -> None:
    """Populate entity_alias from Wikidata. Idempotent and resumable.

    Skips names whose key is already indexed, so an interrupted run costs nothing
    to repeat — which matters because this is one HTTP round trip per name.
    """
    have = {r["alias_norm"] for r in await c.fetch("SELECT DISTINCT alias_norm FROM entity_alias")}
    todo = [e for e in ents if alias_key(e["name"]) not in have][:limit]
    print(f"  index holds {len(have)} keys; {len(todo)} names to look up")
    for i, e in enumerate(todo, 1):
        try:
            qids = search(e["name"], limit=3)
        except Exception as exc:  # noqa: BLE001 — one bad name must not end the run
            print(f"    ! search {e['name']!r}: {exc}")
            continue
        if not qids:
            # Record the miss so a rerun does not pay for it again. A self-pointing
            # row with a sentinel qid would pollute the index, so the miss is stored
            # against the key with an empty qid and filtered out at match time.
            await c.execute(
                "INSERT INTO entity_alias (alias_norm, qid, prior, surface) VALUES ($1,'',0,$2)"
                " ON CONFLICT DO NOTHING", alias_key(e["name"]), e["name"])
            continue
        try:
            items = fetch_aliases(qids)
        except Exception as exc:  # noqa: BLE001
            print(f"    ! aliases {qids}: {exc}")
            continue
        rows = [
            (alias_key(n), qid, None, d["prior"], n, kind)
            for qid, d in items.items() for n, kind in d["forms"].items()
            if alias_key(n) != "unknown"
        ]
        await c.executemany(
            "INSERT INTO entity_alias (alias_norm, qid, lang, prior, surface, kind)"
            " VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (alias_norm, qid)"
            " DO UPDATE SET prior = $4, kind = $6",
            rows)
        if i % 25 == 0:
            print(f"    {i}/{len(todo)} … {len(rows)} forms from {e['name'][:32]!r}")


async def refresh_index(c) -> None:
    """Rewrite every surface form for the QIDs already in the index.

    Cheap and separate from --fetch on purpose: the expensive half is the one
    search per entity NAME, and that result is captured the moment a QID lands in
    the index. Re-deriving forms for known QIDs is a handful of batched calls, so
    changing how forms are ranked does not cost a full re-crawl.
    """
    qids = [r["qid"] for r in await c.fetch("SELECT DISTINCT qid FROM entity_alias WHERE qid <> ''")]
    if not qids:
        return
    items = fetch_aliases(qids)
    rows = [
        (alias_key(n), qid, None, d["prior"], n, kind)
        for qid, d in items.items() for n, kind in d["forms"].items()
        if alias_key(n) != "unknown"
    ]
    await c.execute("DELETE FROM entity_alias WHERE qid = ANY($1::text[])", list(items))
    await c.executemany(
        "INSERT INTO entity_alias (alias_norm, qid, lang, prior, surface, kind)"
        " VALUES ($1,$2,$3,$4,$5,$6) ON CONFLICT (alias_norm, qid)"
        " DO UPDATE SET prior = $4, kind = $6", rows)
    print(f"  refreshed {len(items)} QIDs -> {len(rows)} surface forms")


async def prune_non_agents(c) -> None:
    """Drop index entries for candidates that are neither people nor organizations.

    Our entity table holds only those two types, so anything else is a candidate we
    could never correctly link to — and search returns plenty. They do real damage
    by manufacturing FALSE ambiguity: "BJP" matched both the party and the British
    Journal of Pharmacology, and since the tie could not be broken on evidence the
    entity was refused, losing the largest IDF fix available to a pharmacology
    journal.

    Run after --fetch, and idempotent, so it also cleans an index built before this
    filter existed.
    """
    qids = [r["qid"] for r in await c.fetch("SELECT DISTINCT qid FROM entity_alias WHERE qid <> ''")]
    if not qids:
        return
    keep = agent_qids(qids)
    drop = sorted(set(qids) - keep)
    print(f"  index candidates: {len(qids)}   people/orgs: {len(keep)}   pruning {len(drop)}")
    if drop:
        await c.execute("DELETE FROM entity_alias WHERE qid = ANY($1::text[])", drop)


# A recorded canonical name outranks a recorded nickname outranks a derived form.
TIER = ("label", "sitelink", "alias")

# Words an initialism skips. Not a stoplist for meaning — just the joining words
# English acronyms drop: "Press Trust of India" -> PTI, not PTOI.
_JOINERS = {"of", "and", "the", "for", "in", "on", "at", "de", "da", "el", "la"}


def is_identifying(key: str, kind: str, labels: list[str]) -> bool:
    """Is this surface form specific enough to identify the item on its own?

    A single-token ALIAS is the weakest evidence Wikidata offers, and it is where
    the false merges live. Q114270322 is a Kashmiri poet, Hemangi Sharma, whose
    item lists both "Rahul" and "Kiran" as aliases — so two unrelated people in our
    corpus were folded into a poet neither of them is.

    But single-token aliases are also the folds worth the most: bjp, cjp, dmk, cbi,
    rss, nta. What separates those from "Rahul" is that each is DERIVED FROM the
    item's own name — an initialism of it, or one of its words:

        bjp    <- Bharatiya Janata Party        initialism
        pti    <- Press Trust of India          initialism (joiners skipped)
        vijay  <- C. Joseph Vijay               a word of the name
        rahul  <- Hemangi Sharma                neither, so refused

    Labels and wiki titles are exempt: those ARE the item's name, so the question
    does not arise. Multi-token aliases are exempt too — "Press Trust of India" is
    specific enough on its own, and the tier rule already covers the case where a
    multi-word alias belongs to a different entity (CPI vs CPI(Marxist)).
    """
    if kind != "alias" or "-" in key:
        return True
    for lab in labels:
        words = [w for w in alias_key(lab).split("-") if w]
        if key in words:
            return True
        if key == "".join(w[0] for w in words if w not in _JOINERS):
            return True
    return False


def resolve(cands: list[tuple[str, str]]) -> tuple[str, str] | None:
    """Decide one surface form's QID from its candidates, or refuse.

    `cands` is [(qid, kind)]. Returns (qid, resolution), or None for "cannot tell".

    1. One candidate QID -> link it.
    2. Several -> only the STRONGEST tier present competes, so a label match is
       never dragged into a tie by some other item's alias. Wikidata alias sets are
       not identity-preserving: Q234277 is the CPI(Marxist) and carries plain
       "Communist Party of India" as an alias — a different party that still
       exists, and one our corpus names separately. The real CPI's own LABEL is
       that string, so the tier separates them where a raw match cannot.
    3. Still several -> REFUSE.

    An earlier version broke the tie on prominence (sitelink count), which is
    exactly how "Communist Party of India" became the CPI(Marxist): 52 sitelinks
    against 46. That is the absence-of-evidence trap this repo keeps relearning — a
    weak signal used to manufacture a confident answer out of "I cannot tell". The
    cost of refusing is an entity left on its slug, which is today's behaviour; the
    cost of a wrong fold is two parties merged permanently, with nothing raised.

    Refusing is load-bearing for genuine ambiguity too. "CPI" alone really does
    name both parties in Indian coverage (and, per Wikidata, an isolated cleft
    palate), so no rule should resolve it.

    Prominence is not a parameter here, deliberately: the signal that caused the
    wrong fold is not available to be reached for again.
    """
    if not cands:
        return None
    if len({q for q, _ in cands}) == 1:
        return cands[0][0], "alias_exact"
    rank = {k: i for i, k in enumerate(TIER)}
    weakest = len(TIER) - 1
    best = min(rank.get(k, weakest) for _, k in cands)
    strong = {q for q, k in cands if rank.get(k, weakest) == best}
    if len(strong) == 1:
        return next(iter(strong)), f"{TIER[best]}_wins"
    return None


def narrow(cands: list[tuple[str, str]], ctx: dict) -> tuple[list[tuple[str, str]], list[str]]:
    """Drop candidates a current-India corpus cannot mean, but only ever narrowing.

    Applied BEFORE `resolve`, not inside it, so `resolve` keeps taking nothing but
    (qid, kind) and the prominence signal that caused a wrong fold stays
    structurally out of reach.

    Each step only takes effect if it removes something AND leaves something —
    never empties the set, never invents a candidate. If narrowing still leaves two,
    `resolve` refuses exactly as before, so this can convert a refusal into a link
    but never a link into a different link.

    Liveness first, because it is close to a fact: given a live candidate and a
    defunct one, current news means the live one. Country second and only if
    liveness did not settle it, because it is a prior rather than a fact — Pakistani
    and other non-Indian entities are legitimately covered here, and this must not
    become a blanket preference for India. It fires only where the NAME has already
    failed, e.g. the Indian and Pakistani parties both called "Aam Aadmi Party".
    """
    applied: list[str] = []

    def keep(tag: str, pred) -> None:
        nonlocal cands
        kept = [c for c in cands if pred(c[0])]
        if kept and len({q for q, _ in kept}) < len({q for q, _ in cands}):
            cands = kept
            applied.append(tag)

    keep("live", lambda q: not ctx.get(q, {}).get("defunct"))
    if len({q for q, _ in cands}) > 1:
        keep("india", lambda q: INDIA in ctx.get(q, {}).get("countries", ()))
    return cands, applied


async def match(c, ents: list[dict]) -> tuple[dict, list[tuple]]:
    """entity id -> (qid, resolution) via `resolve`, plus the refusals.

    Two passes. The first resolves on the name alone; the second asks Wikidata for
    context on ONLY the candidate sets that stayed ambiguous, so the extra lookup
    is one query for a few hundred items instead of a property fetch over the whole
    index.
    """
    # An item's own recorded names, taken from the index itself — the rows whose
    # kind is 'label' ARE the labels, so this needs no extra column or lookup.
    labels: dict[str, list[str]] = {}
    for r in await c.fetch(
        "SELECT qid, surface FROM entity_alias WHERE qid <> '' AND kind = 'label'"
    ):
        labels.setdefault(r["qid"], []).append(r["surface"])

    idx: dict[str, list[tuple[str, str]]] = {}
    weak = 0
    for r in await c.fetch(
        "SELECT alias_norm, qid, kind, surface FROM entity_alias WHERE qid <> ''"
    ):
        kind = r["kind"] or "alias"
        if not is_identifying(r["alias_norm"], kind, labels.get(r["qid"], [])):
            weak += 1
            continue
        idx.setdefault(r["alias_norm"], []).append((r["qid"], kind))
    if weak:
        print(f"  dropped {weak} single-token aliases not derived from their item's name")

    linked: dict = {}
    unresolved: list[tuple[dict, list[tuple[str, str]]]] = []
    for e in ents:
        cands = idx.get(alias_key(e["name"]))
        if not cands:
            continue
        got = resolve(cands)
        if got:
            linked[e["id"]] = got
        else:
            unresolved.append((e, cands))

    refused: list[tuple] = []
    if unresolved:
        qids = sorted({q for _, cands in unresolved for q, _ in cands})
        try:
            ctx = entity_context(qids)
        except Exception as exc:  # noqa: BLE001
            # Losing the context lookup must cost recall, never precision: without
            # it every one of these stays refused, which is the pre-existing
            # behaviour. It must not fall through to some looser rule.
            print(f"  ! context lookup failed ({exc}); {len(unresolved)} stay refused")
            ctx = {}
        n_rescued = 0
        for e, cands in unresolved:
            narrowed, applied = narrow(cands, ctx)
            got = resolve(narrowed) if applied else None
            if got:
                linked[e["id"]] = (got[0], f"{got[1]}+{'+'.join(applied)}")
                n_rescued += 1
            else:
                refused.append((e["name"], e["df"], sorted({q for q, _ in cands})))
        if n_rescued:
            print(f"  context resolved {n_rescued} of {len(unresolved)} ambiguous names")
    return linked, refused


def fold_groups(ents: list[dict], linked: dict) -> list[list[dict]]:
    """Entities that are one entity, by QID or by separator-identical slug.

    The QID path only folds variants Wikidata has recorded, and it does not record
    everything: "Brijbhushan Sharan Singh" is not an alias of Q4967969 even though
    "Brij Bhushan Sharan Singh" is its label. Those unrecorded variants are the
    residual left after linking, and in production they were still putting three
    spellings of one man in a single story's cast.

    The second key catches them without asking Wikidata anything: two slugs that
    are identical once separators are removed are the same name written two ways.
    That is the same conservative principle `canonical_entity_name` already applies
    to punctuation, one level up — no fuzzy distance, no edit threshold, just a
    difference that carries no information.

    The third key is `common/entity_aliases.py`, the curated list this whole module
    set out to replace. It stays because it encodes the one thing neither Wikidata
    nor a separator rule can supply: judgement about spellings that genuinely
    differ. Devanagari romanisation is not standardised, so जनता reaches us as both
    "Janta" and "Janata" — cockroachjantaparty and cockroachjanataparty are not
    separator-identical, and Wikidata records only one of them. Left out, the
    product kept showing "Cockroach Janata Party" AND "Cockroach Janta Party" in a
    single story's cast, which is the defect that started this work. `entity_slug`
    already resolves new mentions through this list; the fold now cleans up the
    rows that predate it.

    A group holding two DIFFERENT QIDs is refused outright, even though the slugs
    match. Wikidata saying "these are distinct items" is stronger evidence than a
    space, and production has a real case: thawar-chand-gehlot is Q7711496 while
    thawarchand-gehlot is Q107433711. Those are near-certainly duplicate items for
    one person, but resolving that is Wikidata's job, not a fold's.
    """
    parent = {e["id"]: e["id"] for e in ents}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb

    for key in (
        lambda e: (linked.get(e["id"]) or (None,))[0],   # QID, when linked
        lambda e: e["slug"].replace("-", ""),             # the same name, respaced
        lambda e: resolve_alias(e["slug"]),               # curated spelling variants
    ):
        seen: dict = {}
        for e in ents:
            k = key(e)
            if k is None:
                continue
            if k in seen:
                union(e["id"], seen[k])
            else:
                seen[k] = e["id"]

    out: dict = {}
    for e in ents:
        out.setdefault(find(e["id"]), []).append(e)
    groups = []
    for members in out.values():
        if len(members) < 2:
            continue
        qids = {(linked.get(m["id"]) or (None,))[0] for m in members} - {None}
        if len(qids) > 1:
            print(f"  refusing to fold {[m['slug'] for m in members]}: "
                  f"Wikidata has them as {sorted(qids)}")
            continue
        groups.append(members)
    return groups


async def report(c, ents: list[dict], linked: dict, refused: list) -> None:
    # A LIST, not a dict keyed on qid. Keying on the qid silently collapsed every
    # group folded on slug alone into one entry — they share the placeholder key —
    # so a run with 18 groups reported 3. The report is what decisions are made
    # from, so it must not undercount the thing being decided.
    groups = [
        ((linked.get(g[0]["id"]) or (None,))[0] or "slug-variant", g)
        for g in fold_groups(ents, linked)
    ]

    n_lab = sum(1 for v in linked.values() if v[1].endswith("_wins"))
    print(f"\n  entities considered : {len(ents)}")
    print(f"  linked to a QID     : {len(linked)}  ({len(linked)/max(len(ents),1):.0%})"
          f"   of which won on rank: {n_lab}")
    print(f"  REFUSED (ambiguous) : {len(refused)}   left on their slug, deliberately")
    for name, df, qids in sorted(refused, key=lambda r: -r[1])[:6]:
        print(f"      {name[:38]:38} df {df:3}  -> {', '.join(qids[:4])}")
    print(f"  groups holding >1 row: {len(groups)}   (these are the splits that fold)")

    if not groups:
        return
    print("\n  IDF distortion — how much more distinctive a split makes an actor look.")
    print("  true df is the union of the group's events, not the sum: an event naming")
    print("  both spellings must not be counted twice.\n")
    worst = 0.0
    for qid, es in sorted(groups, key=lambda kv: -sum(e["df"] for e in kv[1]))[:15]:
        true_df = await c.fetchval(
            "SELECT count(DISTINCT event_id) FROM event_entities WHERE entity_id = ANY($1::uuid[])",
            [e["id"] for e in es])
        top = max(e["df"] for e in es)
        distortion = true_df / top if top else 1.0
        worst = max(worst, distortion)
        names = ", ".join(f"{e['slug']}({e['df']})" for e in sorted(es, key=lambda x: -x["df"]))
        print(f"    {qid:11} true df {true_df:4}  vs largest part {top:4}  = {distortion:.2f}x")
        print(f"                {names[:96]}")
    print(f"\n  worst distortion in the top groups: {worst:.2f}x")


async def fold(c, ents: list[dict], linked: dict, journal: str, *, write: bool) -> None:
    """Repoint every mention of a QID's variant rows onto one canonical row.

    This is what turns a recorded identity into a measured effect: all six IDF
    sites key on `entity_id`, so one real-world entity has to BE one row for the
    1/df weighting to be right. Repointing means none of those six queries — each
    carrying performance annotations earned the hard way — needs rewriting.

    The canonical is the variant with the most event links, so the majority of
    mentions do not move and the fewest possible rows change. Ties break on id:
    SQL row order is not guaranteed, and a canonical that varied between runs would
    make the fold unreproducible.

    A JOURNAL of every (table, row, old entity) is written before the first write.
    A repoint is otherwise irreversible — `article_entities` stores no surface form,
    so once a mention points at the canonical, nothing records which variant it came
    from. The variant entity ROW survives (other tables may reference it, and
    chasing every foreign key to clear a row nobody reads is work for its own sake),
    but the mention edges do not, which is what the file is for.
    """
    groups = [sorted(es, key=lambda e: (-e["df"], str(e["id"])))
              for es in fold_groups(ents, linked)]
    if not groups:
        print("  nothing to fold")
        return

    # The WHOLE row, not just its id. The repoint below removes rows that would
    # collide with one the canonical already holds, so those rows do not exist
    # afterwards and an id alone could never restore them — replaying it would
    # silently no-op and look like a successful rollback. Storing the columns makes
    # `--unfold` able to re-insert what was removed.
    entries = []
    for canon, *variants in groups:
        for v in variants:
            for tbl in ("event_entities", "article_entities", "impacts"):
                for r in await c.fetch(f"SELECT * FROM {tbl} WHERE entity_id = $1", v["id"]):
                    row = {k: (str(x) if x is not None else None) for k, x in dict(r).items()}
                    entries.append({"table": tbl, "row": row, "to": str(canon["id"])})
    print(f"  {len(groups)} groups -> {len(entries)} mentions move onto {len(groups)} rows")
    if not write:
        print("  (dry run — nothing written; --fold --write applies it)")
        return

    with open(journal, "w") as fh:
        json.dump({"format": JOURNAL_FORMAT, "entries": entries}, fh, indent=1)
    print(f"  journal written: {journal}  ({len(entries)} reversible edges)")

    async with c.transaction():
        for canon, *variants in groups:
            for v in variants:
                for tbl, key in (("event_entities", "event_id"), ("article_entities", "article_id")):
                    # Repoint only where it would not collide with a row the canonical
                    # already holds — (key, entity_id) is unique — then clear the rest.
                    await c.execute(
                        f"""UPDATE {tbl} SET entity_id = $1 WHERE entity_id = $2
                            AND NOT EXISTS (SELECT 1 FROM {tbl} t2
                                            WHERE t2.{key} = {tbl}.{key} AND t2.entity_id = $1)""",
                        canon["id"], v["id"])
                    await c.execute(f"DELETE FROM {tbl} WHERE entity_id = $1", v["id"])
                await c.execute("UPDATE impacts SET entity_id = $1 WHERE entity_id = $2",
                                canon["id"], v["id"])
                # The redirect, without which this fold decays. The variant row
                # survives on purpose, so `_resolve_entity` would send the next
                # article naming it straight back here and reopen the split — the
                # measurement would stay true only until the next ingest.
                await c.execute("UPDATE entities SET merged_into = $1 WHERE id = $2",
                                canon["id"], v["id"])
    print(f"  FOLDED: {len(entries)} mentions repointed, {len(groups)} redirects set")


# Bumped whenever the journal's shape changes. `unfold` refuses anything else.
JOURNAL_FORMAT = "prism-entity-fold/2"


async def unfold(c, journal: str, *, write: bool) -> None:
    """Undo a fold from its journal. The rollback the fold's safety claim depends on.

    Two cases per journalled row, because the fold did two different things:

      repointed  the row still exists with the canonical's entity_id -> put the
                 original entity_id back.
      removed    the row collided with one the canonical already held and was
                 deleted -> re-insert it verbatim.

    The second case is why the journal stores whole rows. An id-only journal would
    UPDATE nothing for a deleted row, report success, and leave the mention gone —
    a rollback that appears to work is worse than none, because it is trusted.

    `merged_into` is cleared too, otherwise ingest would keep redirecting to the
    canonical and the unfold would undo the data but not the behaviour.
    """
    doc = json.load(open(journal))
    if not isinstance(doc, dict) or doc.get("format") != JOURNAL_FORMAT:
        # Refuse rather than guess. An older journal stored only row ids, and the
        # fold DELETES rows that would collide — so replaying ids would UPDATE
        # nothing for exactly the rows that need restoring, and report success. A
        # rollback that appears to work is worse than one that admits it cannot.
        raise SystemExit(
            f"{journal}: not a {JOURNAL_FORMAT} journal. Refusing to restore from a "
            f"format that cannot re-insert deleted rows."
        )
    entries = doc["entries"]
    by_table: dict[str, list[dict]] = {}
    for e in entries:
        by_table.setdefault(e["table"], []).append(e)
    print(f"  journal: {len(entries)} rows across {', '.join(sorted(by_table))}")

    missing = 0
    for tbl, rows in by_table.items():
        ids = [r["row"]["id"] for r in rows]
        present = {
            str(x) for x in await c.fetchval(
                f"SELECT coalesce(array_agg(id), '{{}}') FROM {tbl} WHERE id = ANY($1::uuid[])",
                ids,
            )
        }
        missing += len(ids) - len(present)
    print(f"  {len(entries) - missing} rows to repoint, {missing} to re-insert")
    if not write:
        print("  (dry run — nothing written; --unfold --write applies it)")
        return

    restored = 0
    async with c.transaction():
        for tbl, rows in by_table.items():
            for e in rows:
                # `json_populate_record` rather than a column list of parameters:
                # the journal is JSON, so every value in it is a string, and
                # asyncpg refuses a string for a timestamptz parameter. Handing
                # Postgres the whole object lets it coerce each field against the
                # table's own row type — no per-column casting to keep in sync with
                # the schema, and it stays correct when a column is added.
                await c.execute(
                    f"INSERT INTO {tbl} SELECT * FROM json_populate_record(NULL::{tbl}, $1::json)"
                    f" ON CONFLICT (id) DO UPDATE SET entity_id = EXCLUDED.entity_id",
                    json.dumps(e["row"]),
                )
                restored += 1
        await c.execute(
            "UPDATE entities SET merged_into = NULL WHERE id = ANY($1::uuid[])",
            sorted({e["row"]["entity_id"] for e in entries}),
        )
    print(f"  UNFOLDED: {restored} rows restored, redirects cleared")


async def repoint(url: str | None = None, apply: bool = False) -> None:
    """Move mentions off folded entity rows onto the row that survived.

    `fold` repoints everything that exists when it runs. Anything ingested AFTER
    it lands on the dead row again if the attach path does not follow the fold —
    which it did not until 2026-09-04, so a single ingestion run left 31 such
    mentions. The consumer is fixed; this clears what it already wrote, and is
    safe to re-run whenever the count above is non-zero.
    """
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(url or _prod_url(), timeout=90)
    try:
        stale = await c.fetchval(
            "SELECT count(*) FROM event_entities ee JOIN entities e ON e.id = ee.entity_id "
            "WHERE e.merged_into IS NOT NULL")
        print(f"  mentions on folded rows: {stale}")
        if not stale or not apply:
            if stale and not apply:
                print("  DRY RUN — re-run with --apply")
            return
        async with c.transaction():
            # ON CONFLICT: the canonical row may already carry this event, in which
            # case the duplicate is dropped rather than the update failing.
            moved = await c.fetchval(
                """
                WITH m AS (
                    UPDATE event_entities ee SET entity_id = e.merged_into
                    FROM entities e
                    WHERE e.id = ee.entity_id AND e.merged_into IS NOT NULL
                      AND NOT EXISTS (SELECT 1 FROM event_entities x
                                      WHERE x.event_id = ee.event_id
                                        AND x.entity_id = e.merged_into)
                    RETURNING 1) SELECT count(*) FROM m
                """)
            dropped = await c.fetchval(
                """
                WITH d AS (
                    DELETE FROM event_entities ee USING entities e
                    WHERE e.id = ee.entity_id AND e.merged_into IS NOT NULL
                    RETURNING 1) SELECT count(*) FROM d
                """)
        print(f"  repointed {moved}, dropped {dropped} already-present duplicates")
    finally:
        await c.close()


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fetch", action="store_true", help="query Wikidata to fill the index")
    ap.add_argument("--refresh", action="store_true",
                    help="re-derive surface forms for known QIDs (cheap; no re-search)")
    ap.add_argument("--prune", action="store_true",
                    help="drop index entries that are neither people nor organizations")
    ap.add_argument("--write", action="store_true", help="persist qid/resolution on entities")
    ap.add_argument("--fold", action="store_true",
                    help="repoint mentions of variant rows onto one canonical row")
    ap.add_argument("--unfold", action="store_true", help="undo a fold from its journal")
    ap.add_argument("--journal", default="entity_fold.json")
    ap.add_argument("--min-df", type=int, default=2)
    ap.add_argument("--limit", type=int, default=400, help="max names to look up per --fetch run")
    ap.add_argument("--repoint", action="store_true",
                    help="move mentions off folded rows onto the survivor (dry-run)")
    ap.add_argument("--index-url", default=None,
                    help="hold the alias index in a DIFFERENT database from the corpus")
    a = ap.parse_args()

    # Repoint stands alone: it needs no alias index and no Wikidata, only the
    # corpus, so it runs before the heavier setup below.
    if a.repoint:
        await repoint(None, apply=a.write)
        return

    # The alias index is a CACHE of public Wikidata, not corpus data, so it does
    # not have to live beside the corpus it is used against. Separating them is
    # what lets production be measured entirely read-only: the index is built and
    # written locally, and the production connection only ever reads.
    c = await asyncpg.connect(_db_url(), timeout=60)
    ic = await asyncpg.connect(a.index_url, timeout=60) if a.index_url else c
    try:
        corpus_writes = a.write or a.fold or a.unfold
        if a.unfold and not a.write:
            # The dry run must be protected the same way every other one is.
            await c.execute("SET default_transaction_read_only = on")
            print("READ-ONLY — the corpus connection refuses writes.")
        if a.unfold:
            await unfold(c, a.journal, write=a.write)
            return
        if not corpus_writes:
            await c.execute("SET default_transaction_read_only = on")
            print("READ-ONLY — the corpus connection refuses writes.")
        if ic is not c:
            print(f"  alias index held separately: {re.sub(r'//[^@]+@', '//[REDACTED]@', a.index_url)}")
        ents = await load_entities(c, a.min_df)
        print(f"  person/organization entities with df >= {a.min_df}: {len(ents)}")
        if a.fetch:
            await fetch_index(ic, ents, a.limit)
        if a.refresh:
            await refresh_index(ic)
        if a.fetch or a.prune:
            await prune_non_agents(ic)
        linked, refused = await match(ic, ents)
        await report(c, ents, linked, refused)
        if a.write:
            await c.executemany(
                "UPDATE entities SET qid = $2, resolution = $3 WHERE id = $1",
                [(eid, q, r) for eid, (q, r) in linked.items()])
            print(f"\n  WROTE qid on {len(linked)} entities.")
        if a.fold:
            await fold(c, ents, linked, a.journal, write=a.write)
        elif not a.write:
            print("\n  Nothing written. --write persists qid; --fold repoints mentions.")
    finally:
        await c.close()
        if ic is not c:
            await ic.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
