"""The gate on the brief's citations: rounds to qualify on, a batch to label, a score.

correlation/cites.py decides, for every line of the free brief, which report it
restates and whether every figure in it is in that report (shadow, in
projection.lens_cites). Nothing reaches a reader until people say those answers
are good. The task is `brief_support`: one line, the report it was written from,
"does this report say this?" (common/label_guides.py).

    uv run python -m tools.gold_brief_cites --rounds                  # dry run: what the practice round and test would hold
    uv run python -m tools.gold_brief_cites --rounds --apply          # write both CLOSED; then label_qualify --check/--publish
    uv run python -m tools.gold_brief_cites --push "Brief lines — round 1" --apply   # the work batch (unlisted)
    uv run python -m tools.label_admin --list KEY                     # show it on the dashboard
    uv run python -m tools.label_qualify --seed-checks WORK --from TEST --apply      # hidden checks, one in ten
    uv run python -m tools.gold_brief_cites --score KEY               # the gate, from the batch's answers

THE ROUNDS ARE ANSWERED BY CONSTRUCTION. There is no founder-labelled gold for
this task, and one person's opinion is never a test answer (tools/label_qualify).
So every item's answer is made, not judged, from English single-report records:
  YES — the line IS a sentence of the report.
  NO  — the same kind of sentence with one figure changed to one the report
        never prints; or with a claim appended that the report never makes; or
        a sentence from a different story's report, shown against this one.
Half and half, so answering always Yes or always No fails.

THE WORK BATCH IS STRATIFIED on the machine's verdict so both sides of the gate
are read: lines it evidences from a one-report record, lines it matched among
several, lines with a figure no cited report has, and lines it could cite to
nothing (shown against the report whose words come closest). The machine's
verdict rides in the payload under "_" keys, which the API strips before a
labeller sees the task.

THE GATE. A line the machine evidences will print as reported, with its [n]. A
false Yes there is the costly error (a line shown as the report's that the
report does not say), so precision of "evidenced" must reach 0.995 (the trust
plan's target). The other rows are printed, not gated.

Reads production read-only unless --apply.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import random
import re
import secrets
import sys
import uuid

import asyncpg

from correlation.cites import _words, cite_lines, figures, split_lines

KIND = "brief_support"
GATE = 0.995
PRACTICE_SIZE = 8
POOL_SIZE = 40
SAMPLE = {"single": 70, "matched": 60, "figure_missing": 35, "uncited": 35}
EXCERPT_CHARS = 700
TEXT_CHARS = 12000
ADDITIONS = (
    ", the first time this has happened in a decade",
    ", officials said after a four-hour meeting",
    ", with the decision taken unanimously",
    ", the highest figure on record",
    ", three days earlier than planned",
)
_USABLE = re.compile(r"^[A-Z\"“].{60,280}[.!?][\"”’]?$")


def excerpt(line: str, text: str) -> str:
    """The report's passage closest to the line: the best sentence and its neighbours."""
    sents = split_lines(" ".join((text or "").split()))
    if not sents:
        return ""
    want = _words(line) | figures(line)
    best = max(range(len(sents)), key=lambda i: len(want & (_words(sents[i]) | figures(sents[i]))))
    out = " ".join(sents[max(0, best - 1): best + 2])
    return out if len(out) <= EXCERPT_CHARS else out[:EXCERPT_CHARS].rsplit(" ", 1)[0] + " …"


def usable_sentences(text: str) -> list[str]:
    return [s for s in split_lines(" ".join((text or "").split())) if _USABLE.match(s) and len(s.split()) >= 10]


def swap_figure(sentence: str, report_text: str, rng: random.Random) -> tuple[str, str, str] | None:
    """The sentence with one figure changed to a number the report never prints."""
    nums = [m for m in re.finditer(r"\d[\d,]*(?:\.\d+)?", sentence) if not re.fullmatch(r"(19|20)\d\d", m.group())]
    if not nums:
        return None
    m = rng.choice(nums)
    old = m.group()
    digits = old.replace(",", "")
    value = float(digits)
    for factor in (2, 3, 1.5, 0.5, 4):
        new_val = value * factor
        new = f"{new_val:,.0f}" if "." not in digits and new_val == int(new_val) else f"{new_val:.1f}"
        if "," not in old:
            new = new.replace(",", "")
        if new != old and new.replace(",", "") not in figures(report_text):
            return sentence[: m.start()] + new + sentence[m.end():], old, new
    return None


def add_claim(sentence: str, report_text: str, rng: random.Random) -> tuple[str, str] | None:
    """The sentence with a claim appended that the report never makes."""
    body = sentence.rstrip("\"”’")
    if not body.endswith("."):
        return None
    lower = report_text.lower()
    for extra in rng.sample(ADDITIONS, len(ADDITIONS)):
        if extra.strip(", ").lower() not in lower:
            return body[:-1] + extra + ".", extra.strip(", ")
    return None


def _report(r: dict) -> dict:
    text = " ".join((r["clean_text"] or "").split())
    return {"title": r["title"], "outlet": r["source"], "language": r["language_name"], "code": r["lang"] or "",
            "url": r["url"], "text": text[:TEXT_CHARS]}


def construct(reports: list[dict], rng: random.Random) -> list[dict]:
    """Items with answers made, not judged. `reports`: English one-report records."""
    items: list[dict] = []
    for i, r in enumerate(reports):
        text = " ".join((r["clean_text"] or "").split())
        sents = usable_sentences(text)
        if len(sents) < 3:
            continue
        rep = _report(r)
        story = r["event_title"]

        def item(line: str, yes: bool, why: str, story=story, rep=rep, text=text, gold=str(r["event_id"])) -> dict:
            return {"payload": {"kind": KIND, "line": line, "story": story,
                                "report": {**rep, "excerpt": excerpt(line, text)}},
                    "yes": yes, "gold": gold, "explanation": why, "languages": ["en"]}

        yes_s = rng.choice(sents)
        items.append(item(yes_s, True, f"The line is the report's own sentence: “{yes_s}”"))
        with_figs = [s for s in sents if s != yes_s and swap_figure(s, text, rng)]
        if with_figs:
            s = rng.choice(with_figs)
            changed, old, new = swap_figure(s, text, rng)
            items.append(item(changed, False, f"The report says {old}; the line says {new}. That figure is not the report's."))
        rest = [s for s in sents if s != yes_s]
        added = add_claim(rng.choice(rest), text, rng) if rest else None
        if added:
            items.append(item(added[0], False, f"Everything but “{added[1]}” is the report's. That part is not in it."))
        others = [o for j, o in enumerate(reports) if j != i and o["event_id"] != r["event_id"]]
        rng.shuffle(others)
        mine = _words(text)
        for o in others[:5]:
            cand = usable_sentences(o["clean_text"])
            cand = [s for s in cand if len(_words(s) & mine) <= 1 and not (figures(s) & figures(text))]
            if cand:
                s = rng.choice(cand)
                items.append(item(s, False, f"This line is from another story ({o['event_title']}); the report never mentions it."))
                break
    return items


def balance(items: list[dict], n: int, rng: random.Random, exclude: set[str]) -> list[dict]:
    yes = [it for it in items if it["yes"] and it["gold"] not in exclude]
    no = [it for it in items if not it["yes"] and it["gold"] not in exclude]
    rng.shuffle(yes)
    rng.shuffle(no)
    half = n // 2
    picked = yes[:half] + no[: n - min(len(yes), half)]
    rng.shuffle(picked)
    return picked


_RECORDS = """
    SELECT e.id AS event_id, e.title AS event_title, e.projection -> 'lens_briefs' ->> 'reader' AS brief
    FROM events e WHERE e.projection -> 'lens_briefs' ->> 'reader' IS NOT NULL
    ORDER BY e.last_updated_at DESC LIMIT $1
"""
_REPORTS = """
    SELECT em.event_id, a.id AS article_id, a.clean_text, ri.title, ri.url, ri.language AS lang, s.name AS source
    FROM event_memberships em JOIN articles a ON a.id = em.article_id
    JOIN raw_items ri ON ri.id = a.raw_item_id JOIN sources s ON s.id = ri.source_id
    WHERE em.event_id = ANY($1::uuid[])
"""


async def _load(c: asyncpg.Connection, limit: int) -> tuple[list, dict]:
    from common.languages import display_name

    records = await c.fetch(_RECORDS, limit)
    by_event: dict = {}
    for r in await c.fetch(_REPORTS, [rec["event_id"] for rec in records]):
        by_event.setdefault(r["event_id"], []).append({**dict(r), "language_name": display_name(r["lang"]) or "unknown"})
    return records, by_event


async def rounds(c: asyncpg.Connection, seed: int, apply: bool) -> None:
    from common.label_scoring import PASS_MARK, QUESTIONS_PER_TEST
    from tools.label_qualify import fair, write_round

    records, by_event = await _load(c, 1500)
    singles = [{**by_event[rec["event_id"]][0], "event_title": rec["event_title"]}
               for rec in records if len(by_event.get(rec["event_id"], [])) == 1
               and by_event[rec["event_id"]][0]["lang"] == "en"]
    rng = random.Random(seed)
    rng.shuffle(singles)
    items = construct(singles[:80], rng)
    practice = balance(items, PRACTICE_SIZE, rng, set())
    pool = balance(items, POOL_SIZE, rng, {it["gold"] for it in practice})
    for label, rnd in (("practice", practice), ("test pool", pool)):
        n_yes = sum(it["yes"] for it in rnd)
        print(f"  {label}: {len(rnd)} items, {n_yes} yes / {len(rnd) - n_yes} no; constant strategies: "
              + ", ".join(f"{k} {v:.0%}" for k, v in fair(rnd).items()))
    if any(v >= PASS_MARK for v in fair(pool).values()) or len(pool) < QUESTIONS_PER_TEST:
        raise SystemExit("refusing: the test pool is passable without reading, or too small")
    for it in pool[:4]:
        print(f"    e.g. {'YES' if it['yes'] else 'NO '}  {it['payload']['line'][:90]}  — {it['explanation'][:70]}")
    if apply:
        pk = await write_round(c, "practice", "Practice — Does the report say this?", practice, KIND)
        qk = await write_round(c, "qualify", "Test — Does the report say this?", pool, KIND)
        print(f"  written CLOSED: practice {pk}, test {qk}. Next: label_qualify --check / --publish each.")


def stratum(line: dict) -> str:
    if line["supported"]:
        return "single" if line["method"] == "single" else "matched"
    return "figure_missing" if line["cites"] else "uncited"


async def push(c: asyncpg.Connection, name: str, seed: int, apply: bool) -> None:
    records, by_event = await _load(c, 1500)
    pools: dict[str, list] = {k: [] for k in SAMPLE}
    for rec in records:
        reps = by_event.get(rec["event_id"], [])
        if not reps:
            continue
        for line in cite_lines(rec["brief"], [(r["article_id"], r["clean_text"]) for r in reps]):
            st = stratum(line)
            if line["cites"]:
                shown = next(r for r in reps if str(r["article_id"]) == line["cites"][0])
            else:  # the report whose words come closest
                words = _words(line["text"])
                shown = max(reps, key=lambda r: len(words & _words(r["clean_text"] or "")))
            pools[st].append((rec, line, shown))
    rng = random.Random(seed)
    picked = []
    for st, n in SAMPLE.items():
        rng.shuffle(pools[st])
        picked += [(st, *x) for x in pools[st][:n]]
    rng.shuffle(picked)  # a labeller must not read the machine's answer from the order
    print("  available: " + ", ".join(f"{k} {len(v)}" for k, v in pools.items()))
    if not apply:
        print(f"DRY RUN: would write {len(picked)} tasks to a new unlisted batch {name!r}. Add --apply.")
        return
    key, bid = secrets.token_urlsafe(9), uuid.uuid4()
    async with c.transaction():
        await c.execute(
            "INSERT INTO label_batches (id, key, name, kind, purpose, open, self_join, listed, notes) "
            "VALUES ($1, $2, $3, $4, 'work', true, false, false, $5)",
            bid, key, name, KIND, "Does the report say this line? Scored by tools/gold_brief_cites --score.")
        for pos, (st, rec, line, shown) in enumerate(picked):
            text = " ".join((shown["clean_text"] or "").split())
            payload = {"kind": KIND, "line": line["text"], "story": rec["event_title"],
                       "report": {**_report(shown), "excerpt": excerpt(line["text"], text)},
                       "_machine": {"stratum": st, "method": line["method"], "supported": line["supported"]},
                       "_event_id": str(rec["event_id"]), "_article_id": str(shown["article_id"])}
            await c.execute(
                "INSERT INTO label_tasks (id, batch_id, position, candidates, payload, languages) "
                "VALUES ($1, $2, $3, '[]'::jsonb, $4::jsonb, $5::text[])",
                uuid.uuid4(), bid, pos, json.dumps(payload, ensure_ascii=False),
                sorted({"en", shown["lang"] or "en"}))
    print(f"wrote {len(picked)} tasks to batch {key!r} ({name}), unlisted.")
    print(f"next: tools.label_qualify --seed-checks {key} --from TEST_KEY --apply; tools.label_admin --list {key}")


def gate(rows: list[dict]) -> bool:
    """rows: {"stratum", "label": "y"|"n"}."""
    served = [r for r in rows if r["stratum"] in ("single", "matched")]
    right = [r for r in served if r["label"] == "y"]
    precision = len(right) / len(served) if served else 0.0
    ok = bool(served) and precision >= GATE
    print(f"  evidenced lines labelled {len(served):4}   the report says it: {len(right):4}   "
          f"precision {precision:.3f}   gate {GATE}  {'PASS' if ok else 'FAIL'}")
    for st in ("single", "matched", "figure_missing", "uncited"):
        mine = [r for r in rows if r["stratum"] == st]
        yes = sum(r["label"] == "y" for r in mine)
        print(f"    {st:15} {len(mine):4} labelled   report says it {yes:4}   not {len(mine) - yes:4}")
    print("\nGATE PASSED — the brief may print [n] per line" if ok else "\ngate not passed — citations stay shadow")
    return ok


async def score(c: asyncpg.Connection, key: str) -> int:
    from tools.gold_renderings import labels_from

    rows = await c.fetch(
        """
        SELECT t.id, t.payload, r.selected, r.unsure, r.skipped
        FROM label_tasks t JOIN label_batches b ON b.id = t.batch_id
        LEFT JOIN label_responses r ON r.task_id = t.id
        WHERE b.key = $1 AND t.expected IS NULL
        """, key)
    by_task: dict[str, dict] = {}
    for r in rows:
        payload = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"])
        t = by_task.setdefault(str(r["id"]), {"payload": payload, "responses": []})
        if r["selected"] is not None:
            sel = r["selected"] if isinstance(r["selected"], list) else json.loads(r["selected"])
            t["responses"].append({"selected": sel, "unsure": r["unsure"], "skipped": r["skipped"]})
    labelled = [{"stratum": t["payload"]["_machine"]["stratum"], "label": label}
                for t in by_task.values() if "_machine" in t["payload"] and (label := labels_from(t["responses"]))]
    print(f"  {len(labelled)} of {len(by_task)} tasks carry an agreed label")
    return 0 if gate(labelled) else 1


async def main() -> int:
    from tools.snapshot_l2 import _prod_url

    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--rounds", action="store_true", help="build the practice round and the test pool")
    ap.add_argument("--push", metavar="NAME", help="write the stratified work batch (unlisted)")
    ap.add_argument("--score", metavar="KEY", help="score a labelled batch against the gate")
    ap.add_argument("--apply", action="store_true", help="write; without it nothing is")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    a = ap.parse_args()
    if not (a.rounds or a.push or a.score):
        ap.print_help()
        return 2
    c = await asyncpg.connect(a.db or _prod_url(), timeout=60)
    try:
        if not a.apply:
            await c.execute("SET default_transaction_read_only = on")
        if a.rounds:
            await rounds(c, a.seed, a.apply)
        if a.push:
            await push(c, a.push, a.seed, a.apply)
        if a.score:
            return await score(c, a.score)
        return 0
    finally:
        await c.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
