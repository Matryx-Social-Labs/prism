"""Build the practice rounds and qualification tests labellers must pass (plan phase 3).

    uv run python -m tools.label_qualify --claims                 # dry run: what the pools would hold
    uv run python -m tools.label_qualify --claims --apply         # write them, CLOSED (unpublished)
    uv run python -m tools.label_qualify --from-batch KEY [--apply]   # pools from a founder-labelled batch
    uv run python -m tools.label_qualify --dump KEY > k.json      # every item + its explanation, to edit
    uv run python -m tools.label_qualify --load KEY k.json        # write edited explanations back
    uv run python -m tools.label_qualify --check KEY              # fairness + completeness report
    uv run python -m tools.label_qualify --publish KEY            # open it — refuses if --check fails

WHERE THE ANSWERS COME FROM. Only from answers the founders already agreed on:
tools/gold_claims (founder-ratified 2026-09-14), items marked `agree` or
`adj:high`. `adj:medium` (reported speech with no quotation marks — a product
question, not an attribution one) and one-labeller items are left out: a test
item must have an answer, and those do not have one the founders share.

WHY SOME ANSWERS ARE BUILT. The claims gold is 58 yes to 1 no. A test drawn from
it would pass anyone who always says yes, which is the one labeller this test
exists to stop. So every agreed YES can also become a known NO: the same quote,
asked about ANOTHER person named in the same article. The article credits the
words to the real speaker, so "did this other person say it?" is no — by
construction, not by opinion. The other person must share no name token with
the speaker, or "Shivakumar" vs "D.K. Shivakumar" would become a wrong "no".

FROM A LABELLED BATCH (--from-batch). A kind with no adjudicated gold — the
quote-rendering task, the cross-language task — gets its test from the batch
its first labellers answered: only tasks where at least two people answered
definitely and all agreed. One person's opinion is never a test answer. Those
items carry no explanation; a founder writes them before --publish.

EXPLANATIONS ARE DRAFTS. Each item gets one written from the article's own
words before the quote; a founder reads and edits them (--dump / --load) before
--publish, which refuses while any item has none. Batches are written CLOSED, so
nothing is served until a founder publishes it.

A POOL A CONSTANT STRATEGY CAN PASS IS REFUSED (common/label_scoring).

Reads production read-only unless --apply / --load / --publish.
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

from common.label_scoring import PASS_MARK, QUESTIONS_PER_TEST, constant_strategy_scores
from tools.snapshot_l2 import _prod_url

KIND = "claim_attribution"
TRUSTED = {"agree", "adj:high"}
POOL_SIZE = 40  # the test draws QUESTIONS_PER_TEST from this
PRACTICE_SIZE = 8
WINDOW = 800  # same context window the work task shows (tools/gold_candidates)
_TOKEN = re.compile(r"[^\W\d_]{3,}")


def name_tokens(name: str) -> set[str]:
    return {t.casefold() for t in _TOKEN.findall(name or "")}


def other_people(speaker: str, people: list[str]) -> list[str]:
    """People named in the article who are NOT the speaker — no shared name
    token, so a shortened or titled form of the speaker never counts as someone
    else."""
    mine = name_tokens(speaker)
    seen: set[str] = set()
    out = []
    for p in people:
        if p and not (name_tokens(p) & mine) and p.casefold() not in seen:
            seen.add(p.casefold())
            out.append(p)
    return out


def context(flat: str, quote: str) -> dict[str, str] | None:
    at = flat.find(quote)
    if at < 0:
        return None
    end = at + len(quote)
    return {"context_before": flat[max(0, at - WINDOW):at], "context_after": flat[end:end + WINDOW],
            "lead": "" if at <= WINDOW else flat[:250]}


_END = re.compile(r"[.?!](?=\s|$)|[”\"]")


def whole_quote(flat: str, truncated: str) -> str | None:
    """The gold's truncated quote, extended to the end of its sentence in the
    article. Verbatim either way — it is the article's own text."""
    prefix = " ".join(truncated.replace("[...]", "").split())
    at = flat.find(prefix)
    if at < 0 or len(prefix) < 20:
        return None
    end = at + len(prefix)
    if "[...]" in truncated:
        m = _END.search(flat, end, end + 300)
        end = m.start() + (1 if flat[m.start()] in ".?!" else 0) if m else end
    return flat[at:end].strip()


def attribution_cue(speaker: str, before: str, after: str) -> str:
    """The article's own words that tie the quote to its speaker: the nearest
    mention of any of the speaker's names — first just after the quote ("…, said
    Jose Pradeep"), then just before it ("Pradeep said, …"). Empty when the
    article only says "he" or "she" there, and the draft says so instead."""
    toks = name_tokens(speaker)

    def around(text: str, at: int, width: int = 70) -> str:
        lo, hi = max(0, at - width), min(len(text), at + width)
        return " ".join(text[lo:hi].split()[1:-1]) or text[lo:hi].strip()

    tail = after[:220]
    for m in _TOKEN.finditer(tail):
        if m.group(0).casefold() in toks:
            return around(tail, m.start())
    head = before[-320:]
    hits = [m for m in _TOKEN.finditer(head) if m.group(0).casefold() in toks]
    return around(head, hits[-1].start()) if hits else ""


def explain(yes: bool, speaker: str, asked: str, before: str, after: str = "") -> str:
    cue = attribution_cue(speaker, before, after)
    where = f"the article says “…{cue}…”" if cue else "the words either side of the quote credit it to them"
    if yes:
        return f"Yes. These are {speaker}'s words: {where}."
    return (f"No. These are {speaker}'s words, not {asked}'s: {where}. "
            f"{asked} is named in the same article, but not as the one who said this.")


def balance(yes: list[dict], no: list[dict], n: int, rng: random.Random) -> list[dict]:
    """n items, as close to half yes / half no as the supply allows."""
    rng.shuffle(yes)
    rng.shuffle(no)
    half = n // 2
    take_no = min(len(no), n - min(len(yes), half))
    take_yes = min(len(yes), n - take_no)
    return yes[:take_yes] + no[:take_no]


async def claim_items(c: asyncpg.Connection) -> list[dict]:
    """Every trusted gold claim as a YES item, and a NO item for each that has
    another person named in its article."""
    from tools.gold_claims import CLAIMS

    trusted = [(pos, v) for pos, v in CLAIMS.items() if v[4] in TRUSTED]
    arts = {v[0] for _, v in trusted}
    rows = {
        str(r["id"]): r
        for r in await c.fetch(
            """
            SELECT a.id, a.clean_text, ri.title, ri.language, s.name AS source, en.shared_fields
            FROM articles a JOIN raw_items ri ON ri.id = a.raw_item_id
            JOIN sources s ON s.id = ri.source_id JOIN enrichments en ON en.article_id = a.id
            WHERE a.id = ANY($1::uuid[])
            """, list(arts))
    }
    items: list[dict] = []
    for pos, (aid, speaker, quote_prefix, attributed, _prov) in trusted:
        r = rows.get(aid)
        if r is None:
            continue
        shared = r["shared_fields"] if isinstance(r["shared_fields"], dict) else json.loads(r["shared_fields"] or "{}")
        # The gold keeps the quote truncated. The article is the authority, not
        # the enrichment: these articles have been re-extracted since the gold
        # was adjudicated, and their current claims no longer include the quote.
        flat = " ".join((r["clean_text"] or "").split())
        quote = whole_quote(flat, quote_prefix)
        ctx = context(flat, quote) if quote else None
        if ctx is None:
            continue
        base = {"kind": KIND, "article_id": aid, "title": r["title"], "source": r["source"],
                "language": r["language"] or "en", "quote_text": quote, "article_text": flat, **ctx,
                "target": None, "stance": None}
        items.append({"payload": {**base, "speaker": speaker}, "yes": attributed, "gold": pos,
                      "explanation": explain(attributed, speaker, speaker, ctx["context_before"], ctx["context_after"])})
        if not attributed:
            continue
        people = [e.get("name") for e in shared.get("entities") or [] if isinstance(e, dict) and e.get("type") == "person"]
        people += [cl.get("speaker") for cl in shared.get("claims") or [] if isinstance(cl, dict)]
        for other in other_people(speaker, [p for p in people if p])[:1]:
            items.append({"payload": {**base, "speaker": other}, "yes": False, "gold": pos,
                          "explanation": explain(False, speaker, other, ctx["context_before"], ctx["context_after"])})
    return items


MIN_AGREEING = 2


async def batch_items(c: asyncpg.Connection, key: str) -> tuple[str, list[dict]]:
    """(kind, items) from a labelled payload batch: tasks where at least
    MIN_AGREEING people answered definitely and every definite answer agrees."""
    b = await c.fetchrow("SELECT id, kind FROM label_batches WHERE key = $1", key)
    if b is None:
        raise SystemExit(f"no batch with key {key}")
    rows = await c.fetch(
        """
        SELECT t.id, t.payload, t.languages, r.selected, r.unsure, r.skipped
        FROM label_tasks t JOIN label_responses r ON r.task_id = t.id
        WHERE t.batch_id = $1 AND t.payload IS NOT NULL
        """, b["id"])
    by: dict[str, dict] = {}
    for r in rows:
        t = by.setdefault(str(r["id"]), {"payload": r["payload"], "languages": r["languages"], "votes": []})
        sel = r["selected"] if isinstance(r["selected"], list) else json.loads(r["selected"] or "[]")
        if not r["unsure"] and not r["skipped"]:
            t["votes"].append(bool(sel))
    items = []
    for tid, t in by.items():
        votes = t["votes"]
        if len(votes) >= MIN_AGREEING and len(set(votes)) == 1:
            payload = t["payload"] if isinstance(t["payload"], dict) else json.loads(t["payload"])
            lang = (t["languages"] or [payload.get("language") or "en"])
            items.append({"payload": payload, "yes": votes[0], "gold": tid, "explanation": "", "languages": list(lang)})
    return b["kind"], items


async def write_round(c: asyncpg.Connection, purpose: str, name: str, items: list[dict], kind: str = KIND) -> str:
    key = secrets.token_urlsafe(9)
    bid = uuid.uuid4()
    async with c.transaction():
        await c.execute(
            "INSERT INTO label_batches (id, key, name, kind, purpose, open, self_join, notes) "
            "VALUES ($1, $2, $3, $4, $5, false, false, $6)",
            bid, key, name, kind, purpose,
            "DRAFT explanations — a founder reviews them (--dump / --load) before --publish.")
        for pos, it in enumerate(items):
            tid = uuid.uuid4()
            await c.execute(
                "INSERT INTO label_tasks (id, batch_id, position, candidates, payload, languages, expected, explanation) "
                "VALUES ($1, $2, $3, '[]'::jsonb, $4::jsonb, $5::text[], $6::jsonb, $7)",
                tid, bid, pos, json.dumps(it["payload"]), it.get("languages") or [it["payload"]["language"]],
                json.dumps({"selected": [str(tid)] if it["yes"] else []}), it["explanation"])
    return key


def fair(items: list[dict]) -> dict[str, float]:
    """The constant strategies' scores on a pool, as label_scoring reads it."""
    return constant_strategy_scores(
        [{"id": str(i), "expected": {"selected": [str(i)] if it["yes"] else []}} for i, it in enumerate(items)])


async def check(c: asyncpg.Connection, key: str) -> bool:
    b = await c.fetchrow("SELECT id, purpose, name FROM label_batches WHERE key = $1", key)
    if b is None:
        raise SystemExit(f"no batch with key {key}")
    tasks = await c.fetch("SELECT id, expected, explanation, languages FROM label_tasks WHERE batch_id = $1", b["id"])
    items = [{"id": str(t["id"]), "expected": t["expected"] if isinstance(t["expected"], dict) else json.loads(t["expected"] or "{}")}
             for t in tasks]
    scores = constant_strategy_scores(items)
    missing = sum(1 for t in tasks if not (t["explanation"] or "").strip())
    ok = bool(tasks) and missing == 0 and all(v < PASS_MARK for v in scores.values())
    if b["purpose"] == "qualify":
        ok = ok and len(tasks) >= QUESTIONS_PER_TEST
    print(f"  {b['name']!r} ({b['purpose']}): {len(tasks)} items, {missing} without an explanation")
    for strat, v in scores.items():
        print(f"    {strat:30} would score {v:.0%} {'— FAILS the pass mark, good' if v < PASS_MARK else '— PASSES: refuse'}")
    print(f"  {'OK to publish' if ok else 'NOT publishable'}")
    return ok


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--claims", action="store_true", help="build the claim-attribution practice round and test")
    ap.add_argument("--from-batch", metavar="KEY", help="build a kind's practice round and test from a labelled batch")
    ap.add_argument("--apply", action="store_true", help="with --claims: write the batches (closed)")
    ap.add_argument("--dump", metavar="KEY")
    ap.add_argument("--load", nargs=2, metavar=("KEY", "FILE"))
    ap.add_argument("--check", metavar="KEY")
    ap.add_argument("--publish", metavar="KEY")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    a = ap.parse_args()
    c = await asyncpg.connect(a.db or _prod_url(), timeout=60)
    try:
        if a.claims or a.from_batch:
            if not a.apply:
                await c.execute("SET default_transaction_read_only = on")
            kind, items = (KIND, await claim_items(c)) if a.claims else await batch_items(c, a.from_batch)
            rng = random.Random(a.seed)
            yes = [it for it in items if it["yes"]]
            no = [it for it in items if not it["yes"]]
            # Practice and test never share a gold claim, so practising cannot
            # hand out a test answer.
            practice = balance(yes[:], no[:], PRACTICE_SIZE, rng)
            used = {it["gold"] for it in practice}
            pool = balance([i for i in yes if i["gold"] not in used], [i for i in no if i["gold"] not in used], POOL_SIZE, rng)
            print(f"  {kind}: {len(yes)} yes, {len(no)} no available")
            for label, rnd in (("practice", practice), ("test pool", pool)):
                n_yes = sum(it["yes"] for it in rnd)
                print(f"  {label}: {len(rnd)} items, {n_yes} yes / {len(rnd) - n_yes} no; constant strategies: "
                      + ", ".join(f"{k} {v:.0%}" for k, v in fair(rnd).items()))
            if any(v >= PASS_MARK for v in fair(pool).values()) or len(pool) < QUESTIONS_PER_TEST:
                raise SystemExit("refusing: the test pool is passable without reading, or too small")
            for it in pool[:3]:
                print(f"    e.g. {'YES' if it['yes'] else 'NO '}  {it['payload']['speaker']}: {it['explanation'][:110]}")
            if a.apply:
                pk = await write_round(c, "practice", f"Practice — {kind}", practice, kind)
                qk = await write_round(c, "qualify", f"Test — {kind}", pool, kind)
                print(f"  written CLOSED: practice {pk}, test {qk}. Review with --dump, then --check and --publish.")
        elif a.dump:
            rows = await c.fetch(
                "SELECT t.position, t.payload, t.expected, t.explanation FROM label_tasks t "
                "JOIN label_batches b ON b.id = t.batch_id WHERE b.key = $1 ORDER BY t.position", a.dump)
            out = []
            for r in rows:
                p = r["payload"] if isinstance(r["payload"], dict) else json.loads(r["payload"] or "{}")
                e = r["expected"] if isinstance(r["expected"], dict) else json.loads(r["expected"] or "{}")
                out.append({"position": r["position"], "speaker": p.get("speaker"), "quote": p.get("quote_text"),
                            "answer": "yes" if e.get("selected") else "no", "explanation": r["explanation"]})
            print(json.dumps(out, ensure_ascii=False, indent=1))
        elif a.load:
            key, path = a.load
            edits = json.loads(open(path).read())
            bid = await c.fetchval("SELECT id FROM label_batches WHERE key = $1", key)
            await c.executemany("UPDATE label_tasks SET explanation = $3 WHERE batch_id = $1 AND position = $2",
                                [(bid, e["position"], e["explanation"]) for e in edits])
            print(f"  {len(edits)} explanations written to {key}")
        elif a.check:
            return 0 if await check(c, a.check) else 1
        elif a.publish:
            if not await check(c, a.publish):
                return 1
            await c.execute("UPDATE label_batches SET open = true WHERE key = $1", a.publish)
            print(f"  {a.publish} is open")
        else:
            ap.print_help()
            return 2
        return 0
    finally:
        await c.close()


def demo() -> None:
    """Self-check of the pure parts."""
    assert other_people("D.K. Shivakumar", ["Shivakumar", "Siddaramaiah", "siddaramaiah", ""]) == ["Siddaramaiah"]
    assert other_people("Babar Azam", ["Azam Khan", "Shan Masood"]) == ["Shan Masood"], "a shared surname is not someone else"
    ctx = context("He said the state would double its outlay on roads.", "double its outlay")
    assert ctx and ctx["context_before"].endswith("would ")
    assert context("nothing here", "absent") is None
    art = "He said, “Instead of tracking the lock-in expiry, investors should watch earnings.” Then he left."
    assert whole_quote(art, "Instead of tracking the lock-in expiry, investors should [...]") == \
        "Instead of tracking the lock-in expiry, investors should watch earnings."
    assert whole_quote(art, "not in the article at all, not anywhere [...]") is None
    assert "said Jose Pradeep" in attribution_cue("Jose Pradeep", "the minister spoke. ", ", said Jose Pradeep, the association's president.")
    assert "Pradeep told" in attribution_cue("Jose Pradeep", "Earlier, Pradeep told reporters that ", " and left.")
    assert attribution_cue("Jose Pradeep", "he said ", " he added.") == ""
    rng = random.Random(1)
    yes = [{"yes": True, "gold": i} for i in range(30)]
    no = [{"yes": False, "gold": i} for i in range(5)]
    picked = balance(yes, no, 20, rng)
    assert len(picked) == 20 and sum(not it["yes"] for it in picked) == 5, "every no is used when no is scarce"
    assert fair(picked)["tick everything / always yes"] >= PASS_MARK - 0.2
    print("ok: other people, context, balance")


if __name__ == "__main__":
    if sys.argv[1:] == ["--demo"]:
        demo()
    else:
        sys.exit(asyncio.run(main()))
