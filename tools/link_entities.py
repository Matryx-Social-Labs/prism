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

from common.wikidata import agent_qids, alias_key, fetch_aliases, search


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
    """
    return [dict(r) for r in await c.fetch(
        """
        SELECT e.id, e.slug, e.name, e.qid, count(DISTINCT ee.event_id)::int AS df
        FROM entities e
        JOIN event_entities ee ON ee.entity_id = e.id
        WHERE e.entity_type IN ('person', 'organization')
        GROUP BY e.id, e.slug, e.name, e.qid
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


async def match(c, ents: list[dict]) -> tuple[dict, list[tuple]]:
    """entity id -> (qid, resolution) via `resolve`, plus the refusals."""
    idx: dict[str, list[tuple[str, str]]] = {}
    for r in await c.fetch("SELECT alias_norm, qid, kind FROM entity_alias WHERE qid <> ''"):
        idx.setdefault(r["alias_norm"], []).append((r["qid"], r["kind"] or "alias"))

    linked: dict = {}
    refused: list[tuple] = []
    for e in ents:
        cands = idx.get(alias_key(e["name"]))
        if not cands:
            continue
        got = resolve(cands)
        if got:
            linked[e["id"]] = got
        else:
            refused.append((e["name"], e["df"], sorted({q for q, _ in cands})))
    return linked, refused


async def report(c, ents: list[dict], linked: dict, refused: list) -> None:
    by_qid: dict[str, list[dict]] = {}
    for e in ents:
        got = linked.get(e["id"])
        if got:
            by_qid.setdefault(got[0], []).append(e)
    groups = {q: es for q, es in by_qid.items() if len(es) > 1}

    n_lab = sum(1 for v in linked.values() if v[1].endswith("_wins"))
    print(f"\n  entities considered : {len(ents)}")
    print(f"  linked to a QID     : {len(linked)}  ({len(linked)/max(len(ents),1):.0%})"
          f"   of which won on rank: {n_lab}")
    print(f"  REFUSED (ambiguous) : {len(refused)}   left on their slug, deliberately")
    for name, df, qids in sorted(refused, key=lambda r: -r[1])[:6]:
        print(f"      {name[:38]:38} df {df:3}  -> {', '.join(qids[:4])}")
    print(f"  QIDs holding >1 row : {len(groups)}   (these are the splits that fold)")

    if not groups:
        return
    print("\n  IDF distortion — how much more distinctive a split makes an actor look.")
    print("  true df is the union of the group's events, not the sum: an event naming")
    print("  both spellings must not be counted twice.\n")
    worst = 0.0
    for qid, es in sorted(groups.items(), key=lambda kv: -sum(e["df"] for e in kv[1]))[:15]:
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
    by_qid: dict[str, list[dict]] = {}
    for e in ents:
        if e["id"] in linked:
            by_qid.setdefault(linked[e["id"]][0], []).append(e)
    groups = [sorted(es, key=lambda e: (-e["df"], str(e["id"])))
              for es in by_qid.values() if len(es) > 1]
    if not groups:
        print("  nothing to fold")
        return

    entries = []
    for canon, *variants in groups:
        for v in variants:
            for tbl in ("event_entities", "article_entities", "impacts"):
                entries += [
                    {"table": tbl, "id": str(r["id"]), "from": str(v["id"]), "to": str(canon["id"])}
                    for r in await c.fetch(f"SELECT id FROM {tbl} WHERE entity_id = $1", v["id"])
                ]
    print(f"  {len(groups)} groups -> {len(entries)} mentions move onto {len(groups)} rows")
    if not write:
        print("  (dry run — nothing written; --fold --write applies it)")
        return

    with open(journal, "w") as fh:
        json.dump(entries, fh, indent=1)
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
    print(f"  FOLDED: {len(entries)} mentions repointed")


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
    ap.add_argument("--journal", default="entity_fold.json")
    ap.add_argument("--min-df", type=int, default=2)
    ap.add_argument("--limit", type=int, default=400, help="max names to look up per --fetch run")
    a = ap.parse_args()

    c = await asyncpg.connect(_db_url(), timeout=60)
    try:
        if not (a.fetch or a.write or a.prune or a.refresh):
            await c.execute("SET default_transaction_read_only = on")
            print("READ-ONLY — the connection refuses writes.")
        ents = await load_entities(c, a.min_df)
        print(f"  person/organization entities with df >= {a.min_df}: {len(ents)}")
        if a.fetch:
            await fetch_index(c, ents, a.limit)
        if a.refresh:
            await refresh_index(c)
        if a.fetch or a.prune:
            await prune_non_agents(c)
        linked, refused = await match(c, ents)
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


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
