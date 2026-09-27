"""Re-file the live window after the classification fixes (audit 2026-09-27, P0 #5).

Mint /rss/news, BusinessLine's default feed and ET top stories were declared
business, so their items skipped the gate and the classifier and every one was
filed business with a forced Markets read; cyber facts were stored on any
article; and an event kept its founding article's sector and every member's
state. The pipeline is fixed for what arrives next. This re-files what is
already published, for events updated in the last `--days`:

1. re-classifies those feeds' items with the same Jev call the live
   classifier makes (`--apply` only; one call an item, about $0.0002),
2. drops stored cyber facts from articles not classified tech or cyber,
3. rebuilds every event whose filing changes — sector and subject from its
   members' majority, the states the classifier chose, cyber facts from cyber
   articles only — without re-dating it. No model call.

    DATABASE_URL=postgresql+asyncpg://… uv run python -m tools.backfill_classification          # dry run
    DATABASE_URL=postgresql+asyncpg://… uv run python -m tools.backfill_classification --apply  # + OPENROUTER_API_KEY

The dry run asks no model and cannot write (its transaction is READ ONLY). Its
counts for (2) and (3) are from the classifications as stored; re-classifying
in (1) can only add events to (3). An item the gate now calls not-news keeps
its published record: it is re-filed and listed, because hiding a record is a
separate decision.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from collections import Counter

from sqlalchemy import text

from classification.consumer import _deepen_subject
from classification.decide import (
    QUESTIONS,
    QUESTIONS_VERSION,
    classification_from,
    state_for,
    to_results,
)
from common.db import session_scope
from common.decisions import decide
from common.logging import get_logger
from correlation.consumer import _rebuild_projection, chosen_states, placement
from enrichment.consumer import cyber_classified

logger = get_logger(__name__)
GENERAL_FEEDS = ("livemint", "hindu_businessline", "economictimes")
CONCURRENCY = 8

# Members in the order the projection rebuild reads them, so the plan predicts
# exactly what the rebuild will write.
MEMBERS = text(
    """
    SELECT e.id AS event_id, e.title, e.sector, e.subsector, e.subject_path, e.subject_confidence,
           e.regions, ri.id AS raw_item_id, ri.classification, s.slug, en.id AS enrichment_id,
           COALESCE(en.lens_fields ? 'cyber', false) AS has_cyber
    FROM events e
    JOIN event_memberships em ON em.event_id = e.id
    JOIN articles a ON a.id = em.article_id
    JOIN enrichments en ON en.article_id = a.id
    JOIN raw_items ri ON ri.id = a.raw_item_id
    JOIN sources s ON s.id = ri.source_id
    WHERE e.last_updated_at >= now() - make_interval(days => :days)
    ORDER BY e.id, em.created_at, ri.published_at NULLS LAST, a.id
    """
)


def plan(rows: list[dict], feeds: tuple[str, ...]) -> dict:
    """What the backfill would change, read from the rows as stored."""
    events: dict = {}
    for r in rows:
        events.setdefault(r["event_id"], []).append(r)
    moved, restated = {}, set()
    for eid, members in events.items():
        head = members[0]
        classifications = [m["classification"] or {} for m in members]
        placed = placement(classifications, head["subject_path"], head["subject_confidence"]) or {}
        if placed and (placed["sector"], placed["subject_path"]) != (head["sector"], head["subject_path"]):
            moved[eid] = (head["sector"], placed["sector"], head["title"])
        if chosen_states(classifications) != [r for r in head["regions"] or [] if "-" in r]:
            restated.add(eid)
    return {
        "reclassify": {r["raw_item_id"]: r["event_id"] for r in rows if r["slug"] in feeds},
        "strip": {r["enrichment_id"]: r["event_id"] for r in rows
                  if r["has_cyber"] and not cyber_classified(r["classification"] or {})},
        "moved": moved,
        "restated": restated,
        "events": len(events),
    }


async def _read(days: int, *, read_only: bool) -> list[dict]:
    async with session_scope() as s:
        if read_only:
            await s.execute(text("SET TRANSACTION READ ONLY"))
        return [dict(r) for r in (await s.execute(MEMBERS, {"days": days})).mappings()]


async def _reclassify(item_ids: list) -> tuple[dict, list[str], float, int]:
    """New classification per item, the titles the gate now rejects, cost, failures."""
    async with session_scope() as s:
        items = (await s.execute(text(
            "SELECT ri.id, ri.title, ri.body, s.country FROM raw_items ri JOIN sources s ON s.id = ri.source_id "
            "WHERE ri.id = ANY(:ids)"), {"ids": item_ids})).mappings().all()
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(item):
        meta = {"stage": "backfill", "raw_item_id": str(item["id"]), "questions_version": QUESTIONS_VERSION}
        async with sem:
            try:
                answers = await decide(state_for(item["title"], item["body"]), QUESTIONS,
                                       trace_name="backfill-classify", metadata=meta)
                gate, _ = to_results(answers, source_country=item["country"])
                cls = classification_from(answers, source_country=item["country"])
                cls = await _deepen_subject(cls, item["title"], item["body"], meta)
                return item, cls, gate.is_relevant, answers.usage.cost
            except Exception as exc:  # noqa: BLE001 — an item that fails keeps its old filing; re-run to retry
                logger.warning("backfill_classify_failed", raw_item_id=str(item["id"]), error=str(exc)[:160])
                return item, None, True, 0.0

    done = await asyncio.gather(*(one(i) for i in items))
    new = {item["id"]: cls.model_dump() for item, cls, _, _ in done if cls is not None}
    async with session_scope() as s:
        for item_id, cls in new.items():
            await s.execute(text("UPDATE raw_items SET classification = CAST(:c AS jsonb) WHERE id = :i"),
                            {"c": json.dumps(cls), "i": item_id})
    rejected = [f"{item['id']}  {item['title'][:90]}" for item, cls, relevant, _ in done if cls and not relevant]
    return new, rejected, sum(c for *_, c in done), sum(1 for _, cls, _, _ in done if cls is None)


async def _strip_cyber(enrichment_ids: list) -> None:
    async with session_scope() as s:
        await s.execute(text("UPDATE enrichments SET lens_fields = NULLIF(lens_fields - 'cyber', '{}'::jsonb) "
                             "WHERE id = ANY(:ids)"), {"ids": enrichment_ids})
        await s.execute(text("DELETE FROM field_provenance WHERE enrichment_id = ANY(:ids) "
                             "AND field_path LIKE 'cyber.%'"), {"ids": enrichment_ids})


async def _rebuild(event_ids: set) -> None:
    sem = asyncio.Semaphore(CONCURRENCY)

    async def one(eid):
        async with sem:
            await _rebuild_projection(eid, touch=False)

    await asyncio.gather(*(one(e) for e in event_ids))


def _report(p: dict, feeds: tuple[str, ...], days: int) -> None:
    print(f"events updated in the last {days} days: {p['events']}")
    print(f"  items from {', '.join(feeds)} to re-classify: {len(p['reclassify'])} "
          f"(in {len(set(p['reclassify'].values()))} events; ~${0.0002 * len(p['reclassify']):.2f} of Jev calls)")
    print(f"  cyber facts on articles not classified tech/cyber: {len(p['strip'])} "
          f"(in {len(set(p['strip'].values()))} events)")
    print(f"  events whose sector/subject moves to the members' majority or the path's sector: {len(p['moved'])}")
    for (old, new), n in Counter((o, n) for o, n, _ in p["moved"].values()).most_common(8):
        print(f"      {old or '(none)':>14} -> {new:<14} {n}")
    print(f"  events whose states change to the classifier's majority: {len(p['restated'])}")


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--days", type=int, default=7, help="events updated in this many days (default 7)")
    ap.add_argument("--feeds", default=",".join(GENERAL_FEEDS), help="source slugs to re-classify")
    ap.add_argument("--apply", action="store_true", help="classify and write; without it nothing is")
    args = ap.parse_args()
    feeds = tuple(f.strip() for f in args.feeds.split(",") if f.strip())

    p = plan(await _read(args.days, read_only=not args.apply), feeds)
    _report(p, feeds, args.days)
    if not args.apply:
        print("\nDRY RUN — no model was asked and nothing was written. Re-run with --apply.")
        return 0

    new, rejected, cost, failed = await _reclassify(list(p["reclassify"]))
    print(f"\nre-classified {len(new)} items (${cost:.4f}); {failed} failed and keep their old filing")
    print(f"the gate now calls {len(rejected)} of them not-news (still published; listed for a decision):")
    for line in rejected[:40]:
        print(f"    {line}")
    # Re-read with the new classifications: which cyber facts go, which events move.
    after = plan(await _read(args.days, read_only=False), feeds)
    await _strip_cyber(list(after["strip"]))
    touched = (set(p["reclassify"].values()) | set(after["strip"].values())
               | set(after["moved"]) | after["restated"])
    await _rebuild(touched)
    print(f"dropped {len(after['strip'])} cyber lens facts; rebuilt {len(touched)} events "
          f"({len(after['moved'])} moved sector, {len(after['restated'])} changed states)")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
