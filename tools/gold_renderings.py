"""The gate on quote verdicts: judge the archive in shadow, label a sample, score it.

enrichment/renderings.py asks Jev, per speaker card, whether each quote was
spoken in the language its article printed it in, and whether two quotes in
different languages are one statement. Nothing reaches a reader until labels say
the answers are good (PRISM_QUOTE_VERDICTS stays off on the API until then).

    uv run python -m tools.gold_renderings --judge --limit 20          # dry run: asks, prints, writes nothing
    uv run python -m tools.gold_renderings --judge --apply             # shadow backfill into claim_verdicts
    uv run python -m tools.gold_renderings --push "Quotes — round 1" --apply  # a batch on /label (unlisted until an admin lists it)
    uv run python -m tools.label_admin --languages KEY && uv run python -m tools.label_admin --list KEY
    uv run python -m tools.gold_renderings --score KEY                         # the gate, from the batch's answers

THE LABELLING BATCH. One task per question the model answered, served on the
labeller dashboard as the `quote_rendering` kind (web/src/components/label):

  question=same    — are these two quotes the same statement? (yes = the same)
  question=spoken  — were these words spoken in the language printed? (yes =
                     spoken so; no = the outlet translated them)

It replaced a CSV. A spreadsheet opened scraped quotes as cells, which needed
formula-escaping to be safe; a batch shows them as text, and gets approval,
language gating and the qualification test with it.

The sample is stratified so both sides of each crossing point are read: every
pair the model called the same and an equal number it did not; every quote it
called a translation and an equal number it did not. A random sample would be
almost all "spoken in English, yes" and measure nothing.

THE GATE. Serving turns a quote into "the outlet's translation" and folds one
quote under another, so the costly error is a false YES on either (an original
labelled a translation; two statements merged into one). Precision of the
served verdict must reach 0.95 on each kind. Recall is printed, not gated —
a missed translation leaves today's card, which is the default everywhere else
in this module.

WHAT THE GATE DOES NOT COVER. The sample is ordinary production cards. Quote
text reaches Jev as part of the state, so a hostile outlet could try to steer
one card's verdict. Its reach is bounded by design — a verdict can only mark a
quote as a translation or group two quotes BY THE SAME SPEAKER, never invent
or reattribute words — but a targeted attack on one story is not something a
random-sample precision number measures. Read that before turning the API on.

WRITES TO PRODUCTION only with --apply: --judge --apply (claim_verdicts) and
--push --apply (one new label batch, unlisted). --db points it anywhere else.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import secrets
import sys
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from enrichment import renderings
from tools.snapshot_l2 import _prod_url

GATE = 0.95
SAMPLE_PER_SIDE = 60
EVENT_CONCURRENCY = 8


DB_URL: list[str | None] = [None]  # --db; production when unset


def _engine(read_only: bool):
    url = (DB_URL[0] or _prod_url()).replace("postgresql://", "postgresql+asyncpg://", 1)
    settings = {"default_transaction_read_only": "on"} if read_only else {}
    return create_async_engine(url, connect_args={"server_settings": settings, "timeout": 120})


async def judge(limit: int, apply: bool) -> None:
    """One session per event, committed as it finishes — as the worker does."""
    from sqlalchemy.ext.asyncio import AsyncSession

    engine = _engine(read_only=not apply)
    sem = asyncio.Semaphore(EVENT_CONCURRENCY)
    total, judged, cost = 0, 0, 0.0
    offset, page = 0, 100
    try:
        while not (limit and total >= limit):
            async with AsyncSession(engine) as s:
                events = await renderings.recent_events(s, days=3650, limit=page, offset=offset)
            if not events:
                break
            batch = events[: (limit - total) if limit else None]

            async def one(event_id, title):
                async with sem, AsyncSession(engine) as s:
                    out = await renderings.judge_event(s, event_id, title, write=apply)
                    if apply:
                        await s.commit()
                return title, out

            # Events in parallel: one at a time is ~2 h for the archive over the
            # prod proxy, and each event is its own session either way.
            for title, out in await asyncio.gather(*(one(e, t) for e, t in batch)):
                total += 1
                judged += out["judged"]
                cost += out["cost"]
                if not apply:
                    for key, v in out["verdicts"].items():
                        flagged = [k for k, p in v["spoken"].items() if p < renderings.SPOKEN_MAX]
                        same = [x for x in v["same"] if x[2] >= renderings.SAME_MIN]
                        print(f"  {title[:48]:48} {key[:22]:22} translated={len(flagged)} same={len(same)}")
            offset += page
            print(f"  {total:6d} events   {judged:6d} cards judged   ${cost:.4f}   {'written' if apply else 'DRY RUN'}", flush=True)
    finally:
        await engine.dispose()
    print(f"\n{'wrote' if apply else 'would write'} {judged} cards across {total} events, ${cost:.4f}")


async def push(name: str, seed: int, apply: bool) -> None:
    """Sample from the verdicts first, then read only the sampled quotes, and
    write them as one quote_rendering batch — unlisted, so it reaches nobody
    until an admin lists it (tools/label_admin --list)."""
    engine = _engine(read_only=not apply)
    try:
        async with engine.begin() as conn:
            rows = (await conn.execute(text(
                """
                SELECT cv.event_id, cv.speaker_key, cv.verdicts, e.title
                FROM claim_verdicts cv JOIN events e ON e.id = cv.event_id
                """
            ))).all()

            same_yes, same_no, spoken_no, spoken_yes = [], [], [], []
            for r in rows:
                v = r.verdicts if isinstance(r.verdicts, dict) else json.loads(r.verdicts)
                for a, b, p in v.get("same") or []:
                    (same_yes if p >= renderings.SAME_MIN else same_no).append(("same", p, r, a, b))
                for k, p in (v.get("spoken") or {}).items():
                    (spoken_no if p < renderings.SPOKEN_MAX else spoken_yes).append(("spoken", p, r, k, None))

            rng = random.Random(seed)
            picked = []
            for pool in (same_yes, same_no, spoken_no, spoken_yes):
                rng.shuffle(pool)
                picked += pool[:SAMPLE_PER_SIDE]
            rng.shuffle(picked)  # a labeller must not read the model's answer from the order

            wanted = {k.split(":", 1)[0] for _, _, _, a, b in picked for k in (a, b) if k}
            quotes = await _quotes(conn, wanted)
            if not apply:
                print(f"DRY RUN: would write {len(picked)} tasks to a new unlisted batch {name!r} "
                      "(same 60+60, 60+60 sample). Add --apply to write it.")
                return

            key = secrets.token_urlsafe(9)
            bid = uuid.uuid4()
            await conn.execute(
                text("INSERT INTO label_batches (id, key, name, kind, purpose, open, self_join, listed, notes) "
                     "VALUES (:i, :k, :n, 'quote_rendering', 'work', true, false, false, :notes)"),
                {"i": bid, "k": key, "n": name,
                 "notes": "Same statement in two languages, or a translation? Scored by tools/gold_renderings --score."})
            written = 0
            for kind, p, r, a, b in picked:
                qa, qb = quotes.get(a), quotes.get(b) if b else None
                if qa is None or (b and qb is None):
                    continue  # the report left the event since it was judged
                payload = {"kind": "quote_rendering", "question": kind, "speaker": qa["speaker"], "story": r.title,
                           "a": qa, "b": qb, "model_p": p, "keys": [a, b] if b else [a]}
                langs = sorted({"en", qa["code"], *( [qb["code"]] if qb else [] )} - {""})
                await conn.execute(
                    text("INSERT INTO label_tasks (id, batch_id, position, candidates, payload, languages) "
                         "VALUES (:i, :b, :p, '[]'::jsonb, CAST(:pl AS jsonb), CAST(:l AS text[]))"),
                    {"i": uuid.uuid4(), "b": bid, "p": written, "pl": json.dumps(payload, ensure_ascii=False), "l": langs})
                written += 1
    finally:
        await engine.dispose()
    print(f"wrote {written} tasks to batch {key!r} ({name}): "
          f"same {min(len(same_yes), SAMPLE_PER_SIDE)}+{min(len(same_no), SAMPLE_PER_SIDE)}, "
          f"spoken {min(len(spoken_no), SAMPLE_PER_SIDE)}+{min(len(spoken_yes), SAMPLE_PER_SIDE)}")
    print(f"next: grant the first labellers (tools/label_admin --qualify EMAIL quote_rendering), then --list {key}")


async def _quotes(conn, article_ids: set[str]) -> dict[str, dict]:
    """claim key -> the quote as a labeller needs to read it, for these articles only."""
    from common.languages import display_name

    out: dict[str, dict] = {}
    for src in (await conn.execute(text(
        """
        SELECT a.id AS article_id, s.name AS source_name, ri.language AS lang,
               en.shared_fields -> 'claims' AS claims
        FROM articles a JOIN raw_items ri ON ri.id = a.raw_item_id
        JOIN sources s ON s.id = ri.source_id JOIN enrichments en ON en.article_id = a.id
        WHERE a.id = ANY(CAST(:ids AS uuid[]))
        """
    ), {"ids": sorted(article_ids)})).mappings().all():
        claims = src["claims"]
        claims = json.loads(claims) if isinstance(claims, str) else claims
        for c in claims if isinstance(claims, list) else []:
            if not isinstance(c, dict) or not isinstance(c.get("quote_text"), str):
                continue
            q = c["quote_text"].strip()
            out[renderings.claim_key(str(src["article_id"]), q)] = {
                "speaker": c.get("speaker") or "", "quote": q,
                "language": display_name(src["lang"]) or "unknown", "code": src["lang"] or "",
                "outlet": src["source_name"],
            }
    return out


def gate(rows: list[dict]) -> bool:
    """Precision of the SERVED verdict per question, at the module's crossing
    points. `rows`: {"kind": same|spoken, "model_p": float, "label": "y"|"n"}."""
    ok = True
    for kind, served, served_label in (
        ("same", lambda p: p >= renderings.SAME_MIN, "y"),
        ("spoken", lambda p: p < renderings.SPOKEN_MAX, "n"),
    ):
        mine = [r for r in rows if r["kind"] == kind]
        fired = [r for r in mine if served(float(r["model_p"]))]
        right = [r for r in fired if r["label"] == served_label]
        truly = [r for r in mine if r["label"] == served_label]
        precision = len(right) / len(fired) if fired else 0.0
        recall = len(right) / len(truly) if truly else 0.0
        verdict = "PASS" if fired and precision >= GATE else "FAIL"
        ok &= verdict == "PASS"
        what = "one statement" if kind == "same" else "a translation"
        print(f"  {kind:6}  labelled {len(mine):3}   served as {what}: {len(fired):3}   "
              f"precision {precision:.3f}   recall {recall:.3f}   gate {GATE}  {verdict}")
    print("\nGATE PASSED — PRISM_QUOTE_VERDICTS may be turned on for the API" if ok
          else "\ngate not passed — leave PRISM_QUOTE_VERDICTS off on the API")
    return ok


def labels_from(responses: list[dict]) -> str | None:
    """One task's label from everyone who answered it: the answer every DEFINITE
    answer agrees on, or None. Unsure and skip are not votes; a split is not a
    label (tools/gold_candidates keeps disputes out of gold the same way)."""
    definite = {("y" if r["selected"] else "n") for r in responses if not r["unsure"] and not r["skipped"]}
    return definite.pop() if len(definite) == 1 else None


async def score(key: str) -> int:
    engine = _engine(read_only=True)
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text(
                """
                SELECT t.id, t.payload, r.selected, r.unsure, r.skipped
                FROM label_tasks t JOIN label_batches b ON b.id = t.batch_id
                LEFT JOIN label_responses r ON r.task_id = t.id
                WHERE b.key = :k
                """), {"k": key})).mappings().all()
    finally:
        await engine.dispose()
    by_task: dict[str, dict] = {}
    for r in rows:
        payload = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"])
        t = by_task.setdefault(str(r["id"]), {"payload": payload, "responses": []})
        if r["selected"] is not None:
            sel = r["selected"] if isinstance(r["selected"], list) else json.loads(r["selected"])
            t["responses"].append({"selected": sel, "unsure": r["unsure"], "skipped": r["skipped"]})
    labelled = []
    for t in by_task.values():
        label = labels_from(t["responses"])
        if label:
            labelled.append({"kind": t["payload"]["question"], "model_p": t["payload"]["model_p"], "label": label})
    print(f"  {len(labelled)} of {len(by_task)} tasks carry an agreed label")
    return 0 if gate(labelled) else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--judge", action="store_true", help="ask about every card with quotes")
    ap.add_argument("--apply", action="store_true", help="with --judge or --push: write; without it nothing is")
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    ap.add_argument("--limit", type=int, default=0, help="with --judge: stop after this many events")
    ap.add_argument("--push", metavar="NAME", help="write a stratified quote_rendering batch (unlisted)")
    ap.add_argument("--score", metavar="KEY", help="score a labelled batch against the gate")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    DB_URL[0] = a.db
    if a.judge:
        asyncio.run(judge(a.limit, a.apply))
        return 0
    if a.push:
        asyncio.run(push(a.push, a.seed, a.apply))
        return 0
    if a.score:
        return asyncio.run(score(a.score))
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
