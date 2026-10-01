"""Fold the backlog of spelling variants: one name, one entity (correlation/variants.py).

DRY RUN BY DEFAULT, on a read-only connection. Finds every group of live
person/organisation entities whose names share a key (same entity_type), keeps the
pairs with evidence that both name one thing — the same record, records joined
by a verified follow-up link, or one story of the current partition — asks Jev
about each (one headline per name for context), and writes a CSV to .context/.

  --apply         record every answer in entity_variant_verdicts and fold the
                  "same" ones into the spelling with the most mentions, each fold
                  journalled in its verdict row (one transaction per group, under
                  the attach lock)
  --unfold SLUG   show what undoing the fold of this variant would restore; with
                  --apply, restore it and mark the verdict reverted so nothing
                  folds it again

Every variant is judged against the group's survivor directly — a variant whose
only evidence is with another spelling is listed, not asked (star, never chain).
Idempotent: a folded variant carries merged_into and is not a candidate again, and
a pair already answered is never asked again.

    uv run python -m tools.entity_variants [--db URL] [--max-cost 0.5]
"""

import argparse
import asyncio
import csv
import json
import os
import re
import sys
import uuid

import asyncpg

from common.config import get_settings
from correlation import entity_fold
from correlation.variants import (
    BATCH,
    VARIANT_TYPES,
    Name,
    Pair,
    judge,
    keys,
    rank,
    recorded,
    settle,
)

CONCURRENCY = 4  # Jev allows 1,200 requests a minute; four in flight stay well under


def _db_url(arg: str | None) -> str:
    raw = arg or os.environ.get("DATABASE_URL") or get_settings().database_url
    return re.sub(r"^postgres(ql)?(\+asyncpg)?://", "postgresql://", raw)


async def load_names(c) -> list[Name]:
    """Live entities of the folding types, with their article mentions."""
    rows = await c.fetch(
        """
        SELECT en.id, en.slug, en.name, en.entity_type, count(*)::int AS mentions
        FROM entities en JOIN article_entities ae ON ae.entity_id = en.id
        WHERE en.merged_into IS NULL AND en.entity_type = ANY($1::text[])
        GROUP BY en.id
        """,
        list(VARIANT_TYPES),
    )
    return [Name(r["id"], r["slug"], r["name"], r["entity_type"], r["mentions"]) for r in rows]


def groups(names: list[Name]) -> list[list[Name]]:
    """Names sharing a key within one type, survivor first. Grouping only — the
    judgement is per variant against the survivor."""
    parent = {n.id: n.id for n in names}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    seen: dict[tuple[str, str], uuid.UUID] = {}
    for n in names:
        for k in keys(n.slug):
            first = seen.setdefault((n.kind, k), n.id)
            if first != n.id:
                parent[find(n.id)] = find(first)
    out: dict[uuid.UUID, list[Name]] = {}
    for n in names:
        out.setdefault(find(n.id), []).append(n)
    return [sorted(g, key=rank) for g in out.values() if len(g) > 1]


async def evidence(c, gs: list[list[Name]]) -> dict[frozenset, tuple[str, str, str]]:
    """(kind, variant headline, survivor headline) per (variant, survivor) pair
    with evidence, strongest kind first: the same record, then a verified link,
    then one story of the current partition."""
    ids = [n.id for g in gs for n in g]
    events: dict[uuid.UUID, set] = {}
    for r in await c.fetch("SELECT entity_id, event_id FROM event_entities WHERE entity_id = ANY($1::uuid[])", ids):
        events.setdefault(r["entity_id"], set()).add(r["event_id"])
    evs = sorted({e for s in events.values() for e in s}, key=str)
    title = {r["id"]: r["title"] for r in await c.fetch(
        "SELECT id, title FROM events WHERE id = ANY($1::uuid[])", evs)}
    linked: dict = {}
    for r in await c.fetch(
        "SELECT from_event_id, to_event_id FROM event_links WHERE method = 'verified' "
        "AND (from_event_id = ANY($1::uuid[]) OR to_event_id = ANY($1::uuid[]))", evs,
    ):
        linked.setdefault(r["from_event_id"], set()).add(r["to_event_id"])
        linked.setdefault(r["to_event_id"], set()).add(r["from_event_id"])
    story = {r["event_id"]: r["story_label"] for r in await c.fetch(
        "SELECT es.event_id, es.story_label FROM event_story es "
        "JOIN partition_runs pr ON pr.id = es.run_id AND pr.status = 'current' "
        "WHERE es.event_id = ANY($1::uuid[])", evs)}

    out: dict[frozenset, tuple[str, str, str]] = {}
    for g in gs:
        s = g[0]
        se = events.get(s.id, set())
        for v in g[1:]:
            ve = events.get(v.id, set())
            if shared := sorted(ve & se, key=str):
                out[frozenset((v.id, s.id))] = ("record", title[shared[0]], title[shared[0]])
                continue
            hop = sorted(((a, b) for a in ve for b in linked.get(a, ()) if b in se), key=str)
            if hop:
                out[frozenset((v.id, s.id))] = ("verified_link", title[hop[0][0]], title[hop[0][1]])
                continue
            labels = {story[e]: e for e in sorted(se, key=str) if e in story}
            same = sorted(((a, labels[story[a]]) for a in ve if story.get(a) in labels), key=str)
            if same:
                out[frozenset((v.id, s.id))] = ("story", title[same[0][0]], title[same[0][1]])
    return out


async def named_together(c, gs: list[list[Name]]) -> set[frozenset]:
    """Pairs one article names together: two entities, never asked."""
    ids = [n.id for g in gs for n in g]
    rows = await c.fetch(
        "SELECT a1.entity_id AS a, a2.entity_id AS b FROM article_entities a1 "
        "JOIN article_entities a2 ON a2.article_id = a1.article_id AND a2.entity_id = ANY($1::uuid[]) "
        "WHERE a1.entity_id = ANY($1::uuid[]) AND a1.entity_id <> a2.entity_id", ids)
    return {frozenset((r["a"], r["b"])) for r in rows}


async def ask_all(pairs: list[Pair], max_cost: float) -> tuple[dict[frozenset, tuple[float, str]], float]:
    """Jev over every pair, BATCH to a call, a few calls in flight, stopping
    before a call once the spend reaches `max_cost`. Survivor-major order, so a
    batch holds one group's variants."""
    answers: dict[frozenset, tuple[float, str]] = {}
    spent = 0.0
    gate = asyncio.Semaphore(CONCURRENCY)

    async def one(batch: list[Pair]) -> None:
        nonlocal spent
        async with gate:
            if spent >= max_cost:
                return
            try:
                nouls, model, cost = await judge(batch, metadata={"tool": "entity_variants"})
            except Exception as exc:  # noqa: BLE001 — that batch stays unjudged, listed as such
                print(f"  ! judge failed for {len(batch)} pairs: {str(exc)[:120]}")
                return
            spent += cost
            answers.update({p.key: (n, model) for p, n in zip(batch, nouls, strict=True)})

    await asyncio.gather(*(one(pairs[i:i + BATCH]) for i in range(0, len(pairs), BATCH)))
    return answers, spent


async def unfold(c, slug: str, *, write: bool) -> None:
    variant = await c.fetchval("SELECT id FROM entities WHERE slug = $1", slug)
    rows = await c.fetch(
        "SELECT variant_id, survivor_id, journal FROM entity_variant_verdicts "
        "WHERE journal->>'variant' = $1 AND reverted_at IS NULL", str(variant))
    if not rows:
        print(f"  no fold of {slug!r} to undo")
        return
    for r in rows:
        doc = json.loads(r["journal"])
        print(f"  {slug}: {len(doc['entries'])} rows to restore from the fold into {doc['survivor']}")
    if not write:
        print("  (dry run — --apply restores it)")
        return
    async with c.transaction():
        await c.execute("SELECT pg_advisory_xact_lock(hashtext('correlation.match_or_create'))")
        for r in rows:
            doc = json.loads(r["journal"])
            if doc.get("format") != entity_fold.JOURNAL_FORMAT:
                raise SystemExit(f"journal format {doc.get('format')!r}: refusing to restore")
            await entity_fold.restore(c, doc["entries"])
            await c.execute("UPDATE entities SET merged_into = NULL WHERE id = $1", variant)
            await c.execute(
                "UPDATE entity_variant_verdicts SET reverted_at = now() WHERE variant_id = $1 AND survivor_id = $2",
                r["variant_id"], r["survivor_id"])
    print(f"  UNFOLDED {slug}; its verdict is marked reverted")


def write_csv(path: str, gs, ev, together, verdicts, answers, floor) -> dict[str, int]:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    counts: dict[str, int] = {}
    with open(path, "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["type", "survivor", "survivor_name", "survivor_mentions", "variant", "variant_name",
                    "variant_mentions", "evidence", "variant_seen", "survivor_seen", "noul", "decision"])
        for g in gs:
            s = g[0]
            for v in g[1:]:
                key = frozenset((v.id, s.id))
                kind, vseen, sseen = ev.get(key, ("", "", ""))
                noul = answers[key][0] if key in answers else (verdicts[key]["noul"] if key in verdicts else None)
                if key in together:
                    decision = "named_together"
                elif not kind:
                    decision = "no_evidence"
                elif noul is None:
                    decision = "unjudged"
                elif key in verdicts and verdicts[key]["reverted_at"]:
                    decision = "reverted"
                else:
                    decision = "fold" if noul >= floor else "keep"
                counts[decision] = counts.get(decision, 0) + 1
                w.writerow([s.kind, s.slug, s.name, s.mentions, v.slug, v.name, v.mentions, kind,
                            vseen, sseen, "" if noul is None else f"{noul:.3f}", decision])
    return counts


async def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--apply", action="store_true", help="record verdicts and fold (default: dry run)")
    ap.add_argument("--unfold", metavar="SLUG", help="undo the fold of this variant (with --apply)")
    ap.add_argument("--db", default=None, help="database URL (default: DATABASE_URL)")
    ap.add_argument("--csv", default=".context/entity_variants.csv")
    ap.add_argument("--max-cost", type=float, default=0.5, help="stop asking Jev at this spend (USD)")
    a = ap.parse_args(argv)

    c = await asyncpg.connect(_db_url(a.db), timeout=60)
    try:
        if not a.apply:
            # The server refuses writes even if the code is wrong.
            await c.execute("SET default_transaction_read_only = on")
            print("READ-ONLY — nothing is written to the database.")
        has_table = await c.fetchval("SELECT to_regclass('entity_variant_verdicts') IS NOT NULL")
        if a.unfold:
            await unfold(c, a.unfold, write=a.apply)
            return
        if a.apply and not has_table:
            raise SystemExit("entity_variant_verdicts is missing — run the migration before --apply")

        names = await load_names(c)
        gs = groups(names)
        ev = await evidence(c, gs)
        together = await named_together(c, gs)
        # groups() puts the survivor first (variants.rank).
        pairs = [Pair(v, g[0], *ev[frozenset((v.id, g[0].id))])
                 for g in gs for v in g[1:]
                 if frozenset((v.id, g[0].id)) in ev and frozenset((v.id, g[0].id)) not in together]
        verdicts = await recorded(c, pairs) if has_table else {}
        ask = [p for p in pairs if p.key not in verdicts]
        print(f"  live {', '.join(VARIANT_TYPES)} entities: {len(names)}")
        print(f"  groups sharing a key: {len(gs)} holding {sum(len(g) for g in gs)} spellings")
        print(f"  variant->survivor pairs: {sum(len(g) - 1 for g in gs)}; with evidence {len(ev)} "
              f"({', '.join(f'{k} {sum(1 for e in ev.values() if e[0] == k)}' for k in ('record', 'verified_link', 'story'))})"
              f"; named together by one article {sum(1 for p in together if p in ev)}")
        print(f"  to ask Jev: {len(ask)} (already answered: {len(pairs) - len(ask)})")
        answers, spent = await ask_all(ask, a.max_cost)
        floor = get_settings().prism_entity_variant_min
        counts = write_csv(a.csv, gs, ev, together, verdicts, answers, floor)
        print(f"  judged {len(answers)} pairs for ${spent:.4f}; decisions {counts}")
        print(f"  CSV: {a.csv}")
        if not a.apply:
            print("  Nothing written. --apply records the verdicts and folds.")
            return
        folded = 0
        by_survivor: dict[uuid.UUID, list[Pair]] = {}
        for p in pairs:
            by_survivor.setdefault(p.survivor.id, []).append(p)
        for group in by_survivor.values():
            folded += len(await settle(c, group, {p.key: answers[p.key] for p in group if p.key in answers},
                                       via="backfill", fold=True))
        print(f"  FOLDED {folded} variants (journal in entity_variant_verdicts; --unfold SLUG --apply undoes one)")
    finally:
        await c.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
