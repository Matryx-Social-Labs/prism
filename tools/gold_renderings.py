"""The gate on quote verdicts: judge the archive in shadow, label a sample, score it.

enrichment/renderings.py asks Jev, per speaker card, whether each quote was
spoken in the language its article printed it in, and whether two quotes in
different languages are one statement. Nothing reaches a reader until labels say
the answers are good (PRISM_QUOTE_VERDICTS stays off on the API until then).

    uv run python -m tools.gold_renderings --judge --limit 20          # dry run: asks, prints, writes nothing
    uv run python -m tools.gold_renderings --judge --apply             # shadow backfill into claim_verdicts
    uv run python -m tools.gold_renderings --export gold_renderings.csv
    uv run python -m tools.gold_renderings --score gold_renderings.csv

THE LABELLING SHEET. One row per question the model answered. A founder fills
the `label` column with y or n and nothing else:

  kind=same    — are these two quotes the same statement? (y = the same)
  kind=spoken  — were these words spoken in the language printed? (y = spoken so,
                 n = the outlet translated them)

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

WRITES TO PRODUCTION only with --judge --apply, and only to claim_verdicts.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
import sys
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from enrichment import renderings
from tools.snapshot_l2 import _prod_url

GATE = 0.95
SAMPLE_PER_SIDE = 60


def cell(value: object) -> object:
    """A spreadsheet cannot run it. Quotes, speakers and titles are scraped
    text, and a cell beginning = + - @ (or a tab or CR) is a formula when the
    sheet is opened — a hostile article could make the labeller's own
    spreadsheet fetch a URL with the rest of the row in it."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


def _engine(read_only: bool):
    url = _prod_url().replace("postgresql://", "postgresql+asyncpg://", 1)
    settings = {"default_transaction_read_only": "on"} if read_only else {}
    return create_async_engine(url, connect_args={"server_settings": settings, "timeout": 120})


async def judge(limit: int, apply: bool) -> None:
    """One session per event, committed as it finishes — as the worker does."""
    from sqlalchemy.ext.asyncio import AsyncSession

    engine = _engine(read_only=not apply)
    total, judged, cost = 0, 0, 0.0
    offset, page = 0, 100
    try:
        while not (limit and total >= limit):
            async with AsyncSession(engine) as s:
                events = await renderings.recent_events(s, days=3650, limit=page, offset=offset)
            if not events:
                break
            for event_id, title in events[: (limit - total) if limit else None]:
                async with AsyncSession(engine) as s:
                    out = await renderings.judge_event(s, event_id, title, write=apply)
                    if apply:
                        await s.commit()
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


async def export(path: Path, seed: int) -> None:
    engine = _engine(read_only=True)
    try:
        async with engine.connect() as conn:
            rows = (await conn.execute(text(
                """
                SELECT cv.event_id, cv.speaker_key, cv.verdicts, e.title
                FROM claim_verdicts cv JOIN events e ON e.id = cv.event_id
                """
            ))).all()
            quotes = await _quotes(conn, {str(r.event_id) for r in rows})
    finally:
        await engine.dispose()

    same_yes, same_no, spoken_no, spoken_yes = [], [], [], []
    for r in rows:
        v = r.verdicts if isinstance(r.verdicts, dict) else json.loads(r.verdicts)
        for a, b, p in v.get("same") or []:
            if a in quotes and b in quotes:
                (same_yes if p >= renderings.SAME_MIN else same_no).append(("same", p, r, a, b))
        for k, p in (v.get("spoken") or {}).items():
            if k in quotes:
                (spoken_no if p < renderings.SPOKEN_MAX else spoken_yes).append(("spoken", p, r, k, None))

    rng = random.Random(seed)
    picked = []
    for pool in (same_yes, same_no, spoken_no, spoken_yes):
        rng.shuffle(pool)
        picked += pool[:SAMPLE_PER_SIDE]
    rng.shuffle(picked)  # the labeller must not read the model's answer from row order

    with path.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "kind", "question", "speaker", "story",
                    "a_language", "a_outlet", "a_quote", "b_language", "b_outlet", "b_quote",
                    "model_p", "label"])
        for kind, p, r, a, b in picked:
            qa, qb = quotes[a], quotes.get(b) if b else None
            question = ("Same statement? y/n" if kind == "same"
                        else f"Spoken in {qa['language']} by the speaker (not translated by {qa['outlet']})? y/n")
            w.writerow([cell(v) for v in (
                f"{a}|{b or ''}", kind, question, qa["speaker"], r.title,
                qa["language"], qa["outlet"], qa["quote"],
                qb["language"] if qb else "", qb["outlet"] if qb else "", qb["quote"] if qb else "",
                p, "")])
    print(f"wrote {len(picked)} rows to {path}: "
          f"same {min(len(same_yes), SAMPLE_PER_SIDE)}+{min(len(same_no), SAMPLE_PER_SIDE)}, "
          f"spoken {min(len(spoken_no), SAMPLE_PER_SIDE)}+{min(len(spoken_yes), SAMPLE_PER_SIDE)}")
    print("fill the `label` column with y or n; leave `model_p` alone; do not re-sort before scoring")


async def _quotes(conn, event_ids: set[str]) -> dict[str, dict]:
    """claim key -> the quote as a labeller needs to read it."""
    from common.languages import display_name

    out: dict[str, dict] = {}
    for eid in event_ids:
        for src in (await conn.execute(renderings.CARD_SOURCES, {"eid": eid})).mappings().all():
            claims = src["claims"]
            claims = json.loads(claims) if isinstance(claims, str) else claims
            for c in claims if isinstance(claims, list) else []:
                if not isinstance(c, dict) or not isinstance(c.get("quote_text"), str):
                    continue
                q = c["quote_text"].strip()
                out[renderings.claim_key(str(src["article_id"]), q)] = {
                    "speaker": c.get("speaker") or "", "quote": q,
                    "language": display_name(src["lang"]) or "unknown", "outlet": src["source_name"],
                }
    return out


def score(path: Path) -> int:
    """Precision of the SERVED verdict per kind, at the module's crossing points."""
    rows = [r for r in csv.DictReader(path.open()) if r["label"].strip().lower() in ("y", "n")]
    ok = True
    for kind, served, served_label in (
        ("same", lambda p: p >= renderings.SAME_MIN, "y"),
        ("spoken", lambda p: p < renderings.SPOKEN_MAX, "n"),
    ):
        mine = [r for r in rows if r["kind"] == kind]
        fired = [r for r in mine if served(float(r["model_p"]))]
        right = [r for r in fired if r["label"].strip().lower() == served_label]
        truly = [r for r in mine if r["label"].strip().lower() == served_label]
        precision = len(right) / len(fired) if fired else 0.0
        recall = len(right) / len(truly) if truly else 0.0
        verdict = "PASS" if fired and precision >= GATE else "FAIL"
        ok &= verdict == "PASS"
        what = "one statement" if kind == "same" else "a translation"
        print(f"  {kind:6}  labelled {len(mine):3}   served as {what}: {len(fired):3}   "
              f"precision {precision:.3f}   recall {recall:.3f}   gate {GATE}  {verdict}")
    print("\nGATE PASSED — PRISM_QUOTE_VERDICTS may be turned on for the API" if ok
          else "\ngate not passed — leave PRISM_QUOTE_VERDICTS off on the API")
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--judge", action="store_true", help="ask about every card with quotes")
    ap.add_argument("--apply", action="store_true", help="with --judge: write claim_verdicts")
    ap.add_argument("--limit", type=int, default=0, help="with --judge: stop after this many events")
    ap.add_argument("--export", type=Path, help="write a stratified labelling sheet")
    ap.add_argument("--score", type=Path, help="score a labelled sheet against the gate")
    ap.add_argument("--seed", type=int, default=2026)
    a = ap.parse_args()
    if a.judge:
        asyncio.run(judge(a.limit, a.apply))
        return 0
    if a.export:
        asyncio.run(export(a.export, a.seed))
        return 0
    if a.score:
        return score(a.score)
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
