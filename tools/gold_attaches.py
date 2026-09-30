"""Human labels for the attach decision: is this article the same happening as its record?

The verifier (correlation/verify.py) now decides every fuzzy attach, and until
now it has been measured with itself — Jev scored the old tiers at 44–92%, and
Jev is what replaced them. These labels are the check that is not circular.

The unit is what the pipeline decides: an ARTICLE against the RECORD it was put
in (the record's founding headline and summary). The /label workspace only
shows records against records, so this is a spreadsheet: blind (no tier, no
score), the article's own title beside its English headline and summary.

  uv run python -m tools.gold_attaches --sample 300 --days 7   # after tools.repair_attaches has judged that window
  uv run python -m tools.gold_attaches --push "Attach check" --sheets A.csv B.csv --key <ts>.key.json   # into /label
  uv run python -m tools.gold_attaches --score-batch KEY_A KEY_B --key <ts>.key.json   # answers given in /label
  uv run python -m tools.gold_attaches --score A.csv B.csv --key <ts>.key.json         # answers typed in the sheets

--push puts the two sheets into the /label workspace as two listed batches of
kind attach_identity (the article shown against its record; same / follow-up /
different / not sure). No test exists for the kind, so only founders — who label
without one — see them; one founder takes A, the other B.

--sample stratifies by tier and by Jev's band, so every band the thresholds sit
in is read, and writes two sheets: labeller A rows 1-200, labeller B rows
101-300 (100 in common, for agreement). Answers: same / follow-up / different /
unsure (s, f, d, u). --score reads them back against the key: agreement, the
verifier's precision and recall at each floor, the follow-up links' precision,
and the old tiers' share of the same happening reweighted to the whole window.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import random
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from common.config import get_settings
from tools.repair_attaches import BANDS, FUZZY, _key, answered, band, load

OUT = Path(".context")
# Share of the sample per tier, within each band: entity_overlap carried most
# of the fuzzy attaches and most of the errors.
TIER_WEIGHT = {"entity_overlap": 0.5, "embedding": 0.3, "title_time": 0.2}
FLOORS = (0.5, 0.7, 0.85)
ANSWERS = {"s": "same", "f": "follow-up", "d": "different", "u": "unsure"}
COLUMNS = ["n", "pair", "record_headline", "record_summary", "record_first_reported", "article_outlet",
           "article_published", "article_language", "article_title_as_printed", "article_headline_english",
           "article_summary_english", "answer", "note"]


def stratify(rows: list[dict], cache: dict, n: int, seed: int = 7) -> list[dict]:
    rng = random.Random(seed)
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in rows:
        if _key(r) in cache and r["match_type"] in TIER_WEIGHT:
            cells[(r["match_type"], band(cache[_key(r)][0]))].append(r)
    picked: list[dict] = []
    for _, name in BANDS:
        for tier, w in TIER_WEIGHT.items():
            pool = cells[(tier, name)]
            rng.shuffle(pool)
            picked += pool[: round(n / len(BANDS) * w)]
    rest = [r for pool in cells.values() for r in pool if r not in picked]
    rng.shuffle(rest)
    picked += rest[: max(0, n - len(picked))]
    rng.shuffle(picked)
    return picked[:n]


def _row(i: int, r: dict) -> dict:
    return {
        "n": i, "pair": str(r["membership"]), "record_headline": r["event_title"], "record_summary": r["event_summary"] or "",
        "record_first_reported": f"{r['first_seen_at']:%Y-%m-%d %H:%M}", "article_outlet": r["source"],
        "article_published": f"{r['published_at']:%Y-%m-%d %H:%M}" if r["published_at"] else "",
        "article_language": r["language"] or "", "article_title_as_printed": r["raw_title"],
        "article_headline_english": r["headline"] or "", "article_summary_english": r["article_summary"] or "",
        "answer": "", "note": "",
    }


async def sample(n: int, days: int) -> None:
    rows = await load(days)
    cache = await answered(rows)
    picked = stratify(rows, cache, n)
    population = Counter((r["match_type"], band(cache[_key(r)][0])) for r in rows if _key(r) in cache)
    stamp = f"{datetime.now(UTC):%Y%m%dT%H%M%SZ}"
    OUT.mkdir(exist_ok=True)
    sheets = {"A": picked[:200], "B": picked[100:300]}
    for who, part in sheets.items():
        path = OUT / f"label_attaches_{stamp}_{who}.csv"
        with path.open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(_row(i, r) for i, r in enumerate(part, 1 if who == "A" else 101))
        print(f"wrote {path} ({len(part)} pairs)")
    key = {
        "population": {f"{t}|{b}": c for (t, b), c in population.items()},
        "pairs": {str(r["membership"]): {"tier": r["match_type"], "same": cache[_key(r)][0],
                                         "follows": cache[_key(r)][1]} for r in picked},
    }
    kpath = OUT / f"label_attaches_{stamp}.key.json"
    kpath.write_text(json.dumps(key, indent=1))
    print(f"wrote {kpath} (keep it from the labellers)")
    print("sample:", dict(Counter((r["match_type"], band(cache[_key(r)][0])) for r in picked)))


def _answers(path: Path) -> dict[str, str]:
    out = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            a = (row.get("answer") or "").strip().lower()[:1]
            if a in ANSWERS:
                out[row["pair"]] = ANSWERS[a]
    return out


def kappa(a: list[str], b: list[str]) -> float | None:
    n = len(a)
    if not n:
        return None
    observed = sum(x == y for x, y in zip(a, b, strict=True)) / n
    ca, cb = Counter(a), Counter(b)
    expected = sum(ca[k] * cb[k] for k in set(ca) | set(cb)) / (n * n)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def score(sheets: list[Path], key_path: Path) -> None:
    score_labels([_answers(p) for p in sheets], json.loads(key_path.read_text()))


KIND = "attach_identity"


def _task_payload(row: dict, key: dict) -> dict:
    """What the /label task shows, from a sheet row, and the machine's answer
    under "_" keys (stripped before it is served)."""
    machine = key["pairs"][row["pair"]]
    return {
        "kind": KIND,
        "record": {"headline": row["record_headline"], "summary": row["record_summary"],
                   "first_reported": row["record_first_reported"]},
        "article": {"outlet": row["article_outlet"], "published": row["article_published"],
                    "language": row["article_language"], "title": row["article_title_as_printed"],
                    "headline_english": row["article_headline_english"],
                    "summary_english": row["article_summary_english"]},
        "_pair": row["pair"], "_tier": machine["tier"], "_same": machine["same"], "_follows": machine["follows"],
    }


async def push(name: str, sheets: list[Path], key_path: Path) -> None:
    import secrets
    import uuid

    import asyncpg

    from tools.snapshot_l2 import _prod_url

    key = json.loads(key_path.read_text())
    c = await asyncpg.connect(_prod_url(), timeout=90)
    try:
        for tag, sheet in zip("AB", sheets, strict=False):
            with sheet.open() as f:
                rows = list(csv.DictReader(f))
            bid, batch_key = uuid.uuid4(), secrets.token_urlsafe(9)
            async with c.transaction():
                await c.execute(
                    "INSERT INTO label_batches (id, key, name, kind, purpose, open, self_join, listed, notes) "
                    "VALUES ($1, $2, $3, $4, 'work', true, false, true, $5)",
                    bid, batch_key, f"{name} · {tag}", KIND,
                    "Is this report about the record's happening? Same, follow-up or different. "
                    "Scored by tools/gold_attaches --score-batch.")
                # No language gate: every task carries the report's English
                # rendering beside the title it was printed with.
                await c.executemany(
                    "INSERT INTO label_tasks (id, batch_id, position, candidates, payload) "
                    "VALUES ($1, $2, $3, '[]'::jsonb, $4::jsonb)",
                    [(uuid.uuid4(), bid, i, json.dumps(_task_payload(r, key), ensure_ascii=False))
                     for i, r in enumerate(rows)])
            print(f"batch {tag}: {len(rows)} tasks, key {batch_key}")
    finally:
        await c.close()


async def batch_labels(keys: list[str]) -> list[dict[str, str]]:
    """Each labeller's answers across these batches: pair -> same / follow-up /
    different / unsure. A skip is no answer."""
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(_prod_url(), timeout=90)
    try:
        rows = await c.fetch(
            "SELECT r.labeller, t.payload->>'_pair' AS pair, r.selected, r.unsure, r.skipped "
            "FROM label_responses r JOIN label_tasks t ON t.id = r.task_id JOIN label_batches b ON b.id = t.batch_id "
            "WHERE b.key = ANY($1::text[])", keys)
    finally:
        await c.close()
    by: dict[str, dict[str, str]] = defaultdict(dict)
    for r in rows:
        if r["skipped"]:
            continue
        chosen = (json.loads(r["selected"]) if isinstance(r["selected"], str) else r["selected"]) or []
        by[r["labeller"]][r["pair"]] = "unsure" if r["unsure"] else chosen[0].replace("_", "-") if chosen else "unsure"
    print(f"labellers: {', '.join(f'{k} ({len(v)})' for k, v in by.items())}")
    return list(by.values())


def score_labels(labels: list[dict[str, str]], key: dict) -> None:
    pairs, population = key["pairs"], {tuple(k.split("|")): v for k, v in key["population"].items()}
    if len(labels) == 2:
        both = sorted(set(labels[0]) & set(labels[1]))
        k_same = kappa([labels[0][p] == "same" for p in both], [labels[1][p] == "same" for p in both])
        k_all = kappa([labels[0][p] for p in both], [labels[1][p] for p in both])
        print(f"agreement on {len(both)} pairs read twice: kappa (same vs not) {k_same}, (3-way) {k_all}")
    truth: dict[str, str] = {}
    for p in set().union(*labels):
        if p not in pairs:
            print(f"  ignored: pair {p} is not in the key")
            continue
        votes = {lab[p] for lab in labels if p in lab and lab[p] != "unsure"}
        if len(votes) == 1:
            truth[p] = votes.pop()  # disagreements and unsure are left out, never counted either way
    print(f"{len(truth)} pairs with one agreed answer: {dict(Counter(truth.values()))}")

    same = {p for p, t in truth.items() if t == "same"}
    for floor in FLOORS:
        attach = {p for p in truth if pairs[p]["same"] >= floor}
        prec = len(attach & same) / len(attach) if attach else None
        rec = len(attach & same) / len(same) if same else None
        print(f"verifier at {floor}: attaches {len(attach)}, precision {prec}, recall {rec}")
    follow_min = get_settings().prism_follow_up_min
    linked = {p for p in truth if (pairs[p]["follows"] or 0) >= follow_min and pairs[p]["same"] < get_settings().prism_event_verify_min}
    right = {p for p in linked if truth[p] == "follow-up"}
    print(f"follow-up links at {follow_min}: {len(linked)} written, {len(right)} labelled follow-up")

    print("\nold tiers, share labelled the same happening (by band, then reweighted to the window):")
    for tier in FUZZY:
        cells = {b: [p for p in truth if pairs[p]["tier"] == tier and band(pairs[p]["same"]) == b] for _, b in BANDS}
        if not any(cells.values()):
            continue
        parts, weighted, total = [], 0.0, 0
        for _, b in BANDS:
            got = cells[b]
            share = sum(truth[p] == "same" for p in got) / len(got) if got else None
            parts.append(f"{b} {share if share is None else round(share, 2)} (n={len(got)})")
            if share is not None:
                weighted += share * population.get((tier, b), 0)
                total += population.get((tier, b), 0)
        print(f"  {tier:16} {' · '.join(parts)}  => {weighted / total:.2f} of the window" if total else f"  {tier}: -")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", type=int)
    ap.add_argument("--days", type=int, default=7)
    ap.add_argument("--score", nargs="+", type=Path)
    ap.add_argument("--push", metavar="NAME")
    ap.add_argument("--sheets", nargs="+", type=Path)
    ap.add_argument("--score-batch", nargs="+", metavar="KEY")
    ap.add_argument("--key", type=Path)
    a = ap.parse_args()
    if a.sample:
        asyncio.run(sample(a.sample, a.days))
    elif a.push and a.sheets and a.key:
        asyncio.run(push(a.push, a.sheets, a.key))
    elif a.score_batch and a.key:
        score_labels(asyncio.run(batch_labels(a.score_batch)), json.loads(a.key.read_text()))
    elif a.score and a.key:
        score(a.score, a.key)
    else:
        ap.error("--sample N | --push NAME --sheets A B --key KEY | --score-batch KEY.. --key KEY | --score SHEET.. --key KEY")


if __name__ == "__main__":
    main()
