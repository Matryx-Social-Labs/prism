"""Same-happening labels across languages — the pairs the matcher splits.

Measured on 2026-09-17: 19% of the non-English articles that founded an event
that day had an English twin at IDF word-cosine >= 0.39 on the two EXTRACTED
ENGLISH HEADLINES, and every visible split in the day's news was English vs
Hindi/Kannada/Gujarati/Marathi. The cross-language path in
correlation/clustering.find_event is the entity tier, which needs two shared
person/company/organisation actors — so a story whose actors are countries,
courts and governments cannot bridge at all. A headline tier would; where its
threshold sits is a question for labels, not for an eye reading the band.

  uv run python -m tools.gold_crosslingual --propose [--days 3]   # seeds + candidates
  uv run python -m tools.gold_crosslingual --push NAME             # a label batch, kind event_identity
  uv run python -m tools.gold_crosslingual --compile KEY           # answers -> GOLD_PAIRS lines

Then invite, watch and revoke with tools/gold_candidates (--invite, --status,
--agreement) — the batch is the same shape, the task kind is what differs.

THE TASK IS NARROWER THAN THE STORY TASK. "Same happening" means the same
incident on the same day, reported by another outlet in another language. The
follow-up is a No here (it was a Yes for the story set). The page's primer
says so with examples from this very band.

WHAT THE CANDIDATE NET IS. For each non-English founder: English events within
four days at headline cosine >= 0.30, most similar first, up to four; and when
fewer than two clear that bar, the nearest below it, so that "none of these" is
a real, frequent answer rather than an absent one. Every candidate records its
cosine as its signal, so afterwards the labels can be read against the score
that proposed them — that is the threshold curve this set exists to draw.

WHAT IT COMPILES TO. Article pairs (the seed's founding article, the candidate's
founding article) with True / False, in the shape of tools/gold_pairs.GOLD_PAIRS,
so the existing scorers read it unchanged. A pair two labellers disagreed on is
printed separately and excluded, never recorded as a negative.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import secrets
import sys
import uuid
from pathlib import Path

import asyncpg

from tools.gold_candidates import merge_votes
from tools.snapshot_l2 import _prod_url
from tools.title_cosine import build_idf, cosine

CANDIDATES = Path(".cache/gold_crosslingual.json")
FLOOR, PER_SEED, WINDOW_DAYS = 0.30, 4, 4

FOUNDERS = """
    SELECT e.id::text AS id, e.title, e.sector, ri.language, ri.title AS native, e.created_at,
           en.shared_fields->>'headline' AS xh
    FROM event_memberships m JOIN events e ON e.id = m.event_id
    JOIN articles a ON a.id = m.article_id JOIN raw_items ri ON ri.id = a.raw_item_id
    JOIN enrichments en ON en.article_id = a.id
    WHERE m.match_type = 'new_event' AND ri.language <> 'en' AND ri.language IS NOT NULL
      AND en.shared_fields->>'headline' IS NOT NULL
      AND e.created_at > now() - make_interval(days => $1)
"""
ENGLISH = """
    SELECT e.id::text AS id, e.title, e.created_at
    FROM events e
    WHERE e.headline_by = 'prism' AND e.created_at > now() - make_interval(days => $1)
      AND EXISTS (SELECT 1 FROM event_memberships m JOIN articles a ON a.id = m.article_id
                  JOIN raw_items ri ON ri.id = a.raw_item_id WHERE m.event_id = e.id AND ri.language = 'en')
"""


async def propose(days: int, tasks: int, rng_seed: int = 7) -> None:
    c = await asyncpg.connect(_prod_url(), timeout=90)
    try:
        founders = await c.fetch(FOUNDERS, days + WINDOW_DAYS)
        english = await c.fetch(ENGLISH, days + 2 * WINDOW_DAYS)
    finally:
        await c.close()
    idf = build_idf([e["title"] for e in english] + [f["xh"] for f in founders])
    out = []
    for f in founders:
        scored = []
        for e in english:
            if e["id"] == f["id"] or abs((e["created_at"] - f["created_at"]).days) > WINDOW_DAYS:
                continue
            scored.append((cosine(f["xh"], e["title"], idf), e["id"]))
        scored.sort(reverse=True)
        clear = [(s, i) for s, i in scored if s >= FLOOR][:PER_SEED]
        near = [(s, i) for s, i in scored if s < FLOOR][: max(0, 2 - len(clear))]
        cands = clear + near
        if not cands:
            continue
        out.append({
            "seed": f["id"], "sector": f["sector"], "language": f["language"],
            "candidates": [{"id": i, "signals": [f"headline:{s:.2f}"]} for s, i in cands],
        })
    # A labeller manages ~150 of these in a sitting. Two thirds of the sample
    # from seeds with a candidate in the informative band (>= 0.39, where the
    # matcher would have to decide), a third from seeds with only near-misses,
    # so the set carries real "none" answers and the curve has both ends.
    import random

    rng = random.Random(rng_seed)
    top = lambda o: max(float(c["signals"][0].split(":")[1]) for c in o["candidates"])  # noqa: E731
    hot = [o for o in out if top(o) >= 0.39]
    cold = [o for o in out if top(o) < 0.39]
    rng.shuffle(hot)
    rng.shuffle(cold)
    n_hot = min(len(hot), int(tasks * 2 / 3))
    out = hot[:n_hot] + cold[: tasks - n_hot]
    rng.shuffle(out)
    CANDIDATES.parent.mkdir(exist_ok=True)
    CANDIDATES.write_text(json.dumps(out, indent=1))
    langs: dict[str, int] = {}
    for o in out:
        langs[o["language"]] = langs.get(o["language"], 0) + 1
    print(f"  {len(out)} seeds ({', '.join(f'{k} {v}' for k, v in sorted(langs.items(), key=lambda x: -x[1]))}), "
          f"{sum(len(o['candidates']) for o in out)} candidate pairs -> {CANDIDATES}")


async def push(name: str) -> None:
    cands = json.loads(CANDIDATES.read_text())
    key = secrets.token_urlsafe(9)
    c = await asyncpg.connect(_prod_url(), timeout=90)
    try:
        bid = uuid.uuid4()
        async with c.transaction():
            await c.execute(
                "INSERT INTO label_batches (id, key, name, kind, notes) VALUES ($1,$2,$3,'event_identity',$4)",
                bid, key, name,
                "Tick every headline that reports the SAME happening as the one in bold — the same "
                "incident, the same day, in any language. The follow-up is not the same happening.",
            )
            await c.executemany(
                "INSERT INTO label_tasks (id, batch_id, position, seed_event_id, candidates, sector) "
                "VALUES ($1,$2,$3,$4,$5::jsonb,$6)",
                [(uuid.uuid4(), bid, i, uuid.UUID(o["seed"]), json.dumps(o["candidates"]), o["sector"])
                 for i, o in enumerate(cands)],
            )
    finally:
        await c.close()
    print(f"  batch '{name}': {len(cands)} tasks, kind event_identity")
    print(f"  key: {key}   (now: uv run python -m tools.gold_candidates --invite Name Name --batch {key})")


async def compile_batch(key: str, min_agree: float) -> None:
    c = await asyncpg.connect(_prod_url(), timeout=90)
    try:
        bid = await c.fetchval("SELECT id FROM label_batches WHERE key = $1", key)
        if bid is None:
            raise SystemExit(f"no batch {key}")
        rows = await c.fetch(
            "SELECT t.id, t.seed_event_id::text AS seed, t.candidates, r.selected, r.unsure, r.skipped "
            "FROM label_tasks t JOIN label_responses r ON r.task_id = t.id WHERE t.batch_id = $1", bid)
        total = await c.fetchval("SELECT count(*) FROM label_tasks WHERE batch_id = $1", bid)
        ids = {r["seed"] for r in rows} | {x["id"] for r in rows for x in (json.loads(r["candidates"]) if isinstance(r["candidates"], str) else r["candidates"])}
        founding = {r["eid"]: r["aid"] for r in await c.fetch(
            "SELECT DISTINCT ON (m.event_id) m.event_id::text AS eid, m.article_id::text AS aid "
            "FROM event_memberships m WHERE m.event_id::text = ANY($1::text[]) ORDER BY m.event_id, m.is_survivor DESC, m.created_at",
            list(ids))}
        titles = {r["id"]: r["title"] for r in await c.fetch("SELECT id::text AS id, title FROM events WHERE id::text = ANY($1::text[])", list(ids))}
    finally:
        await c.close()
    by_task: dict = {}
    for r in rows:
        cands = json.loads(r["candidates"]) if isinstance(r["candidates"], str) else r["candidates"]
        e = by_task.setdefault(r["id"], {"seed": r["seed"], "cands": [x["id"] for x in cands],
                                         "score": {x["id"]: x["signals"][0] for x in cands}, "answers": []})
        sel = json.loads(r["selected"]) if isinstance(r["selected"], str) else (r["selected"] or [])
        e["answers"].append(([str(x) for x in sel], bool(r["unsure"]), bool(r["skipped"])))
    pos = neg = 0
    lines, disputed = [], []
    for e in by_task.values():
        definite = [(s, u, k) for s, u, k in e["answers"] if not u and not k]
        if not definite:
            continue
        members, n = merge_votes(e["answers"], e["cands"], min_agree)
        for cid in e["cands"]:
            votes = {cid in sel for sel, _, _ in definite}
            if len(votes) > 1:
                disputed.append((e["seed"], cid))
                continue
            a, b = founding.get(e["seed"]), founding.get(cid)
            if not a or not b:
                continue
            same = cid in members
            pos += same
            neg += not same
            lines.append(f'    ("{a}", "{b}"): {same},  # {e["score"][cid]} · {titles.get(e["seed"], "")[:40]} || {titles.get(cid, "")[:40]}')
    print(f"  batch {key}: {len(by_task)} of {total} tasks answered · {pos} same, {neg} not, {len(disputed)} disputed (excluded)")
    print("\n  # batch 3 — cross-language, September 2026 (tools/gold_crosslingual). Paste into tools/gold_pairs.GOLD_PAIRS")
    print("\n".join(lines))
    if disputed:
        print("\n  # disputed — excluded")
        for a, b in disputed:
            print(f"  # {a} || {b}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--propose", action="store_true")
    ap.add_argument("--days", type=int, default=3, help="founders from the last N days (default 3)")
    ap.add_argument("--tasks", type=int, default=150, help="how many seeds to keep (default 150)")
    ap.add_argument("--push", metavar="NAME")
    ap.add_argument("--compile", metavar="KEY")
    ap.add_argument("--min-agree", type=float, default=0.5)
    a = ap.parse_args()
    if a.propose:
        asyncio.run(propose(a.days, a.tasks))
    elif a.push:
        asyncio.run(push(a.push))
    elif a.compile:
        asyncio.run(compile_batch(a.compile, a.min_agree))
    else:
        ap.print_help()


if __name__ == "__main__":
    sys.exit(main())
