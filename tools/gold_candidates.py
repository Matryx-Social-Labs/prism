"""Propose story-boundary candidates for a human to label, without prejudging them.

    uv run python -m tools.gold_candidates --propose   # sample seeds + neighbours
    uv run python -m tools.gold_candidates --review    # render the review page
    uv run python -m tools.gold_candidates --compile   # decisions -> gold_stories block

WHY THE EXISTING GOLD SET CANNOT SIMPLY BE EXTENDED. `tools/gold_stories` says so
itself: it was labelled off ONE partition group — the Cockroach Janta Party slice —
and its own docstring warns to quote it as "the CJP slice", never as Prism's story
accuracy. That is honest about what it is, and it is also why cross-validation on
it behaves strangely. The two folds are halves of one entangled topic rather than
two samples of the news, and v1 scores F1 0.6571 on fold A against 0.4848 on fold
B. A 0.17 spread between halves means the folds are not comparable, so a 6.5%
difference between algorithms cannot be resolved on it at all.

So this samples the CORPUS, stratified by sector. The current set is entirely
politics; the corpus is 2,073 politics, 1,084 other, 982 business, 475 sports, 183
finance, 174 cybersecurity, 168 health, 154 science, 72 technology, 48
entertainment. Sport and markets are exactly what the existing set says nothing
about, and they behave differently from politics: a match report and a transfer
rumour share a cast without sharing a story.

THE CIRCULARITY TRAP, AND HOW THIS AVOIDS IT. A gold set built from the output of
the algorithm it will judge is worthless — it can only confirm what that algorithm
already believes, and its blind spots become "correct" by construction. So:

  * The production partition is NOT consulted. Not as a seed, not as a candidate,
    not as an ordering.
  * Candidates come from THREE independent proposers — embedding neighbours,
    shared IDF-weighted actors, and title word overlap. Their blind spots differ
    (embeddings miss terse follow-ups; actors miss cross-language coverage of one
    event; titles miss paraphrase), so a pair one misses another usually proposes.
  * Every candidate records WHICH signal proposed it. If the finished labels turn
    out to correlate with one proposer, that is measurable afterwards instead of
    invisible — a gold set containing only pairs the embedding liked would flatter
    the embedding.

WHAT THIS TOOL DOES NOT DO. It does not decide anything. It proposes a seed and its
plausible neighbours with the evidence a person needs — headline, date, sector,
outlet count, distinctive actors — and the judgement stays the human's. Proposing
is mechanical; the label is the product.
"""

from __future__ import annotations

import argparse
import gzip
import html
import json
import random
import re
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from tools.title_cosine import cosine as title_cosine
from tools.title_cosine import load_idf

SNAPSHOT = Path(".cache/l2_snapshot.json.gz")
CANDIDATES = Path(".cache/gold_candidates.json")
REVIEW = Path(".cache/gold_review.html")
DECISIONS = Path(".cache/gold_decisions.json")

WINDOW_DAYS = 21          # a story's developments; beyond this it is a new story
PER_SIGNAL = 5            # neighbours each proposer may contribute
MAX_NEIGHBOURS = 10       # what a person will actually read per seed
DAY = 86400.0

# Floors so a small sector is still represented. Politics dominates the corpus and
# would otherwise dominate the sample, which is how the existing set ended up
# unable to say anything about sport or markets.
SECTOR_TARGET = {
    "politics": 30, "business": 20, "sports": 15, "other": 12,
    "finance": 10, "cybersecurity": 10, "health": 8, "science": 8,
    "technology": 5, "entertainment": 5,
}


def _load():
    from tools.l2 import load

    snap = load()
    with gzip.open(SNAPSHOT, "rt") as fh:
        raw = json.load(fh)
    alt = Path(".cache/l2_me5.npz")
    if alt.exists():
        # mE5 separates gold pairs markedly better than production's encoder
        # (AUC 0.9082 vs 0.7994), so it proposes better neighbours. Used only to
        # SUGGEST — no label depends on it, and two other proposers disagree with
        # it by design.
        snap.emb = np.load(alt)["emb"]
    return snap, raw


def _title_tokens(title: str) -> set[str]:
    """Candidate-generation prefilter only — the SCORE is IDF-weighted below."""
    return {w for w in re.findall(r"\w+", (title or "").casefold()) if len(w) > 3}


def _neighbours(snap, postings, idf, s: int) -> list[tuple[int, set[str]]]:
    """Union of three independent proposers, inside a time window.

    The window is a constraint rather than a signal: coverage 21 days apart is a
    new story even when it names the same people, and including it would ask the
    labeller to adjudicate something the product does not claim.
    """
    ts = snap.ts
    near_time = np.ones(len(snap.ids), dtype=bool)
    if np.isfinite(ts[s]):
        dt = np.abs(ts - ts[s]) / DAY
        near_time = ~np.isfinite(dt) | (dt <= WINDOW_DAYS)

    sig: dict[int, set[str]] = defaultdict(set)

    sims = (snap.emb @ snap.emb[s]).copy()
    sims[~near_time] = -2.0
    sims[s] = -2.0
    for j in np.argsort(-sims)[:PER_SIGNAL]:
        if sims[j] > -1:
            sig[int(j)].add("embedding")

    actor_w: dict[int, float] = defaultdict(float)
    for a in snap.actors[s]:
        w = snap.idf.get(a, 0.0)
        for j in postings.get(a, ()):
            if j != s and near_time[j]:
                actor_w[j] += w
    for j, _ in sorted(actor_w.items(), key=lambda kv: -kv[1])[:PER_SIGNAL]:
        sig[j].add("actors")

    # IDF-weighted, not raw overlap. Raw Jaccard proposed "Gang held for assaulting
    # commuter of government bus" as a neighbour of "Government distributes science
    # kits", because both contain "government" — a word carrying almost no
    # information (idf 4.34 against 7.18 for "distributes"). Sharing a common word
    # is not evidence, and filling a person's screen with those wastes the scarcest
    # resource here, which is their attention.
    seed_toks = _title_tokens(snap.titles[s])
    if seed_toks:
        overlap: dict[int, float] = {}
        for j in np.flatnonzero(near_time):
            if j == s:
                continue
            if seed_toks & _title_tokens(snap.titles[j]):
                c = title_cosine(snap.titles[s], snap.titles[j], idf)
                if c > 0:
                    overlap[int(j)] = c
        for j, _ in sorted(overlap.items(), key=lambda kv: -kv[1])[:PER_SIGNAL]:
            sig[j].add("title")

    # Most-corroborated first: a pair two proposers independently suggest is the
    # one most worth a person's attention.
    return sorted(sig.items(), key=lambda kv: (-len(kv[1]), kv[0]))[:MAX_NEIGHBOURS]


def propose(seed_n: int = 123, rng_seed: int = 7) -> None:
    snap, raw = _load()
    sectors, src = raw["sector"], raw["source_count"]
    rng = random.Random(rng_seed)

    from tools.gold_stories import STORIES

    already = {e for v in STORIES.values() for e in v}

    by_sector: dict[str, list[int]] = defaultdict(list)
    for i, eid in enumerate(snap.ids):
        if eid not in already:
            by_sector[sectors[i] or "other"].append(i)

    # Prefer events several outlets covered, because a story with developments is
    # what the L2 boundary is about — but keep a slice of single-source events so
    # the set contains real singletons to answer "none of these" to.
    seeds: list[int] = []
    for sector, want in SECTOR_TARGET.items():
        pool = by_sector.get(sector, [])
        multi = [i for i in pool if src[i] >= 2]
        single = [i for i in pool if src[i] < 2]
        rng.shuffle(multi)
        rng.shuffle(single)
        n_multi = int(want * 0.8)
        seeds.extend((multi[:n_multi] + single[: want - n_multi])[:want])
    rng.shuffle(seeds)
    seeds = seeds[:seed_n]

    postings: dict[str, list[int]] = defaultdict(list)
    for i, acts in enumerate(snap.actors):
        for a in acts:
            postings[a].append(i)
    idf = load_idf()

    out = []
    for s in seeds:
        near = _neighbours(snap, postings, idf, s)
        if near:
            out.append({
                "seed": snap.ids[s],
                "sector": sectors[s],
                "candidates": [{"id": snap.ids[j], "signals": sorted(g)} for j, g in near],
            })

    CANDIDATES.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATES.write_text(json.dumps(out, indent=1))

    per_sig: dict[str, int] = defaultdict(int)
    per_sec: dict[str, int] = defaultdict(int)
    for o in out:
        per_sec[o["sector"] or "—"] += 1
        for c in o["candidates"]:
            for g in c["signals"]:
                per_sig[g] += 1
    print(f"  seeds {len(out)}   candidate pairs {sum(len(o['candidates']) for o in out)}")
    print(f"  proposed by : {dict(sorted(per_sig.items()))}")
    print(f"  sectors     : {dict(sorted(per_sec.items(), key=lambda kv: -kv[1]))}")
    print(f"  wrote {CANDIDATES}")


def _fmt(ts: float) -> str:
    return "—" if not np.isfinite(ts) else datetime.fromtimestamp(ts, UTC).strftime("%d %b")


def review() -> None:
    """One screen per seed: tick the events belonging to the SAME story.

    Self-contained HTML, no server and no build step. Decisions persist to
    localStorage as you go and export to JSON at the end, so a closed tab does not
    lose the session — labelling 120 seeds is not one sitting.
    """
    snap, raw = _load()
    cands = json.loads(CANDIDATES.read_text())
    idx = snap.index

    def actors_of(i: int) -> str:
        acts = sorted(snap.actors[i], key=lambda a: snap.idf.get(a, 0.0), reverse=True)
        return ", ".join(a.replace("-", " ") for a in acts[:3])

    cards = []
    for n, c in enumerate(cands):
        s = idx[c["seed"]]
        rows = []
        for cand in c["candidates"]:
            j = idx[cand["id"]]
            rows.append(
                f'<label class="c"><input type="checkbox" data-seed="{c["seed"]}" '
                f'data-id="{cand["id"]}"><span class="t">'
                f'{html.escape(snap.titles[j] or "")}</span>'
                f'<span class="m">{_fmt(snap.ts[j])} · {raw["source_count"][j]} outlets · '
                f'{html.escape(actors_of(j))} · <i>{"+".join(cand["signals"])}</i></span></label>'
            )
        cards.append(
            f'<section class="card"><h2>{n + 1}/{len(cands)} '
            f'<span class="sec">{html.escape(c["sector"] or "—")}</span></h2>'
            f'<p class="seed">{html.escape(snap.titles[s] or "")}</p>'
            f'<p class="m">{_fmt(snap.ts[s])} · {raw["source_count"][s]} outlets · '
            f'{html.escape(actors_of(s))}</p>'
            f'<div class="cands">{"".join(rows)}</div></section>'
        )

    REVIEW.write_text(_PAGE.replace("__CARDS__", "\n".join(cards)))
    print(f"  {len(cands)} seeds -> {REVIEW}")
    print("  open it, tick what belongs, press Export, then --compile")


async def push(name: str, url: str | None = None) -> None:
    """Load the proposed candidates into `label_batches` / `label_tasks`.

    Separate from --propose so the same candidate file can be pushed to a local
    database for a rehearsal and to production for the real thing, without
    regenerating and getting a different sample.

    The batch key is `secrets.token_urlsafe`, not a slug of the name. It is the only
    thing standing between a public URL and someone dropping junk into the
    measurement everything else is judged against, so it must not be guessable from
    the batch's title.
    """
    import secrets
    import uuid

    import asyncpg

    from tools.snapshot_l2 import _prod_url

    cands = json.loads(CANDIDATES.read_text())
    key = secrets.token_urlsafe(9)
    c = await asyncpg.connect(url or _prod_url(), timeout=90)
    try:
        bid = uuid.uuid4()
        async with c.transaction():
            await c.execute(
                "INSERT INTO label_batches (id, key, name, kind, notes) "
                "VALUES ($1,$2,$3,'story_boundary',$4)",
                bid, key, name,
                "Tick every headline that is part of the SAME unfolding story as the "
                "one in bold. Same topic is not enough.",
            )
            await c.executemany(
                "INSERT INTO label_tasks (id, batch_id, position, seed_event_id, "
                "candidates, sector) VALUES ($1,$2,$3,$4,$5::jsonb,$6)",
                [
                    (uuid.uuid4(), bid, i, uuid.UUID(o["seed"]),
                     json.dumps(o["candidates"]), o["sector"])
                    for i, o in enumerate(cands)
                ],
            )
    finally:
        await c.close()
    print(f"  batch '{name}': {len(cands)} tasks")
    print(f"  share this link:  /label/{key}")


async def invite(batch_key: str, names: list[str], url: str | None = None,
                 site: str = "https://www.readprism.news") -> None:
    """Mint one credential per named person, for a batch where who answers matters.

    The alternative path is self-join: share the batch link and every visitor is
    issued their own identity automatically. Use this instead when attribution has
    to be certain — the token is bound to a name before anyone opens it, and it can
    be revoked on its own without disturbing the other labellers.
    """
    import secrets
    import uuid

    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(url or _prod_url(), timeout=60)
    try:
        bid = await c.fetchval("SELECT id FROM label_batches WHERE key = $1", batch_key)
        if bid is None:
            raise SystemExit(f"no batch with key {batch_key}")
        for name in names:
            tok = secrets.token_urlsafe(24)
            await c.execute(
                "INSERT INTO label_invites (id, token, batch_id, name) VALUES ($1,$2,$3,$4)",
                uuid.uuid4(), tok, bid, name,
            )
            print(f"  {name:20} {site}/label/{batch_key}#{tok}")
        # Inviting anyone CLOSES self-join. Otherwise the batch key still admits
        # every visitor who receives a forwarded link, and the named invites are
        # decoration on an open door — you would have attribution for the people
        # you asked and none for anyone else.
        await c.execute("UPDATE label_batches SET self_join = false WHERE id = $1", bid)
    finally:
        await c.close()
    print("\n  Send each person only their own line. The part after # is their")
    print("  credential: browsers never send a fragment to the server, so it stays")
    print("  out of access logs and Referer headers, and the page clears it from the")
    print("  address bar once claimed.")
    print("  Self-join is now OFF for this batch — only these people can label.")


def pair_agreement(a: tuple[list[str], bool, bool],
                   b: tuple[list[str], bool, bool]) -> str | None:
    """How two people's answers on ONE task relate. None when not comparable.

    A pair is only comparable when BOTH gave a definite verdict. An `unsure` or a
    skip is not a quiet "no" — scoring it as disagreement would punish the two
    honest answers the form provides, and scoring it as agreement would
    manufacture consensus out of two people declining to answer.
    """
    (sel_a, u_a, sk_a), (sel_b, u_b, sk_b) = a, b
    if u_a or sk_a or u_b or sk_b:
        return None
    return "agree" if set(sel_a) == set(sel_b) else "disagree"


def candidate_kappa(shared: list[tuple[set, set, list[str]]]) -> tuple[float, float, int, int]:
    """Per-candidate agreement and Cohen's kappa over two people's ticks.

    EXACT-SET AGREEMENT ALONE IS MISLEADING and nearly cost this project the gold
    set. On the first 12 shared tasks it read 33%, which looks like two people
    answering at random; per candidate they agreed on 86% of 115 decisions at
    kappa 0.57 — moderate, clearly above chance. With ~10 candidates a task, one
    differing tick fails the whole set, so exact-set punishes near-agreement as
    hard as total disagreement.

    Kappa rather than raw agreement because "leave it" is the overwhelmingly
    common answer: a labeller who ticked nothing at all would score ~0.85 raw and
    kappa 0. Returns (raw, kappa, picks_a, picks_b) — the two pick counts are what
    expose a LUMPER/SPLITTER split, which is systematic and fixable by talking,
    where noise is neither.
    """
    n = agree = pa = pb = 0
    for sel_a, sel_b, cands in shared:
        for cid in cands:
            x, y = cid in sel_a, cid in sel_b
            n += 1
            agree += x == y
            pa += x
            pb += y
    if not n:
        return float("nan"), float("nan"), 0, 0
    po = agree / n
    pe = (pa / n) * (pb / n) + (1 - pa / n) * (1 - pb / n)
    kappa = (po - pe) / (1 - pe) if pe < 1 else float("nan")
    return po, kappa, pa, pb


async def agreement(batch_key: str, url: str | None = None) -> None:
    """Do the labellers actually mean the same thing by "same story"?

    Worth measuring before trusting any of it. On the first five overlapping
    tasks, two labellers agreed once and disagreed once — and the disagreement was
    that one grouped two events because they shared an ORGANISATION. That is the
    exact signal the story layer already over-weights, so a gold set encoding it
    would reward the behaviour the rebuild exists to change.

    EXACT-SET agreement, deliberately harsh. Partial credit would report a
    comfortable number while hiding whether two people draw the boundary in the
    same place, which is the only thing being asked.
    """
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(url or _prod_url(), timeout=90)
    try:
        await c.execute("SET default_transaction_read_only = on")
        rows = await c.fetch(
            """
            SELECT t.position, i.name, r.selected, r.unsure, r.skipped, t.candidates
            FROM label_responses r
            JOIN label_tasks t ON t.id = r.task_id
            JOIN label_invites i ON i.id = r.invite_id
            JOIN label_batches b ON b.id = t.batch_id
            WHERE b.key = $1 AND NOT i.revoked
            ORDER BY t.position
            """,
            batch_key,
        )
    finally:
        await c.close()

    by_task: dict = {}
    for r in rows:
        sel = json.loads(r["selected"]) if isinstance(r["selected"], str) else (r["selected"] or [])
        cands = (json.loads(r["candidates"]) if isinstance(r["candidates"], str)
                 else r["candidates"])
        by_task.setdefault(r["position"], {})[r["name"] or "anonymous"] = (
            [str(x) for x in sel], bool(r["unsure"]), bool(r["skipped"]),
            [x["id"] for x in cands])

    pairs: dict = {}
    for pos, who in sorted(by_task.items()):
        names = sorted(who)
        for i, a in enumerate(names):
            for b in names[i + 1:]:
                verdict = pair_agreement(who[a][:3], who[b][:3])
                rec = pairs.setdefault((a, b), {"agree": 0, "disagree": 0, "skip": 0,
                                                "where": [], "shared": []})
                if verdict is not None:
                    rec["shared"].append((set(who[a][0]), set(who[b][0]), who[a][3]))
                if verdict is None:
                    rec["skip"] += 1
                else:
                    rec[verdict] += 1
                    if verdict == "disagree":
                        rec["where"].append(pos)

    if not pairs:
        raise SystemExit("no task has been answered by two labellers yet")
    print(f"  {len(by_task)} tasks answered; {sum(1 for w in by_task.values() if len(w) > 1)} "
          "seen by more than one person\n")
    for (a, b), r in sorted(pairs.items()):
        n = r["agree"] + r["disagree"]
        rate = f"{r['agree'] / n:.0%}" if n else "n/a"
        print(f"  {a} vs {b}")
        print(f"    comparable {n:>3}   agree {r['agree']:>3} ({rate})   "
              f"disagree {r['disagree']:>3}   not comparable {r['skip']:>3}")
        if r["shared"]:
            po, kappa, pa, pb = candidate_kappa(r["shared"])
            lean = ("" if pa == pb else
                    f"   <- {a if pa > pb else b} ticks "
                    f"{max(pa, pb) / max(min(pa, pb), 1):.1f}x more")
            print(f"    per-candidate {po:.3f}   kappa {kappa:.3f}   "
                  f"picks {pa} vs {pb}{lean}")
        if n and n < 10:
            print(f"    too few to mean anything yet — {10 - n} more shared tasks would help")
        if r["where"]:
            print(f"    disagreed on positions: {r['where'][:12]}")


async def revoke(batch_key: str, name: str, url: str | None = None) -> None:
    """Withdraw one person's credential without disturbing anyone else's.

    Their answers are KEPT, not deleted. A revoked labeller is usually someone
    whose judgements you no longer want to weight, and that is a decision for the
    compile step where it can be seen and argued with — deleting the rows here
    would silently change a measurement everyone downstream treats as data.
    """
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(url or _prod_url(), timeout=60)
    try:
        n = await c.fetchval(
            "WITH d AS (UPDATE label_invites i SET revoked = true "
            "FROM label_batches b WHERE b.id = i.batch_id AND b.key = $1 AND i.name = $2 "
            "AND NOT i.revoked RETURNING 1) SELECT count(*) FROM d",
            batch_key, name,
        )
    finally:
        await c.close()
    print(f"  revoked {n} invite(s) for {name!r}" if n else f"  no active invite named {name!r}")


async def status(batch_key: str, url: str | None = None) -> None:
    """Who was invited, who has actually answered, and how far each has got."""
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(url or _prod_url(), timeout=60)
    try:
        await c.execute("SET default_transaction_read_only = on")
        b = await c.fetchrow(
            "SELECT id, name, open, self_join FROM label_batches WHERE key = $1", batch_key)
        if b is None:
            raise SystemExit(f"no batch with key {batch_key}")
        total = await c.fetchval("SELECT count(*) FROM label_tasks WHERE batch_id = $1", b["id"])
        rows = await c.fetch(
            """
            SELECT i.name, i.revoked, i.last_seen_at,
                   count(r.id) FILTER (WHERE NOT r.skipped) AS done,
                   count(*) FILTER (WHERE r.unsure) AS unsure,
                   count(*) FILTER (WHERE r.skipped) AS skipped
            FROM label_invites i
            LEFT JOIN label_responses r ON r.invite_id = i.id
            WHERE i.batch_id = $1
            GROUP BY i.id, i.name, i.revoked, i.last_seen_at
            ORDER BY count(r.id) DESC, i.name
            """,
            b["id"],
        )
    finally:
        await c.close()
    gate = "OPEN to anyone with the link" if b["self_join"] else "invite-only"
    print(f"  {b['name']!r}: {total} tasks, {gate}, {'accepting' if b['open'] else 'CLOSED'}")
    if not rows:
        print("  nobody has been invited or joined yet")
    for r in rows:
        seen = r["last_seen_at"].strftime("%d %b %H:%M") if r["last_seen_at"] else "never opened"
        flag = "  REVOKED" if r["revoked"] else ""
        print(f"    {(r['name'] or 'anonymous'):20} {r['done']:>4}/{total}  "
              f"unsure {r['unsure']:>3}  skipped {r['skipped']:>3}  "
              f"last seen {seen}{flag}")


def merge_votes(answers: list[tuple[list[str], bool, bool]], candidates: list[str],
                min_agree: float = 0.5) -> tuple[list[str], int]:
    """Turn several people's ticks on ONE task into one verdict.

    Each answer is (selected, unsure, skipped).

    Returns (members, n_definite). MERGING IS A JUDGEMENT, which is why it lives
    here in the open rather than inside the export serializer, and why the two
    rules it encodes are stated rather than assumed:

    UNSURE IS NOT A "NO". An unsure answer is dropped from the denominator
    entirely instead of counting against inclusion. Treating "I cannot tell" as
    "not the same story" is absence-of-evidence reasoning, which this repo has
    been burned by four separate times and which `content_similarity` returns
    None to avoid. A SKIP ("I cannot read this language") is excluded for the same
    reason — it is an answer about the labeller, not about the story. Both
    exclusions live HERE rather than in the caller: a filter applied upstream is a
    merge rule with no test attached, and a mutation that let skips vote went
    unnoticed until this moved in.

    A CANDIDATE NEEDS MORE THAN HALF of the definite answers. With one labeller
    that is simply their opinion; the caller is told `n_definite` so a gold set
    resting on single opinions can say so instead of looking like consensus.
    """
    definite = [sel for sel, unsure, skipped in answers if not unsure and not skipped]
    if not definite:
        return [], 0
    members = [
        c for c in candidates
        if sum(1 for sel in definite if c in sel) / len(definite) > min_agree
    ]
    return members, len(definite)


async def compile_from_batch(batch_key: str, url: str | None = None,
                             min_agree: float = 0.5) -> None:
    """Build a gold_stories block from what people actually answered on the page.

    The offline `--compile` path reads a decisions file written by the local HTML
    review page — one person, one browser. This reads the batch every labeller
    worked through, which is the only path that exists once the work is shared out.

    Revoked labellers are excluded HERE, which is the other half of `--revoke`:
    their answers are kept in the table as a record and simply do not vote.
    """
    import asyncpg

    from tools.snapshot_l2 import _prod_url

    c = await asyncpg.connect(url or _prod_url(), timeout=90)
    try:
        await c.execute("SET default_transaction_read_only = on")
        bid = await c.fetchval("SELECT id FROM label_batches WHERE key = $1", batch_key)
        if bid is None:
            raise SystemExit(f"no batch with key {batch_key}")
        rows = await c.fetch(
            """
            SELECT t.id, t.seed_event_id::text AS seed, t.candidates,
                   r.selected, r.unsure, r.skipped
            FROM label_tasks t
            JOIN label_responses r ON r.task_id = t.id
            JOIN label_invites i ON i.id = r.invite_id
            WHERE t.batch_id = $1 AND NOT i.revoked
            ORDER BY t.position
            """,
            bid,
        )
        total_tasks = await c.fetchval(
            "SELECT count(*) FROM label_tasks WHERE batch_id = $1", bid)
    finally:
        await c.close()

    by_task: dict = {}
    skips = 0
    for r in rows:
        skips += bool(r["skipped"])
        cands = json.loads(r["candidates"]) if isinstance(r["candidates"], str) else r["candidates"]
        entry = by_task.setdefault(
            r["id"], {"seed": r["seed"], "cands": [x["id"] for x in cands], "answers": []})
        sel = json.loads(r["selected"]) if isinstance(r["selected"], str) else (r["selected"] or [])
        entry["answers"].append(
            ([str(x) for x in sel], bool(r["unsure"]), bool(r["skipped"])))

    stories, singles, empties = [], 0, 0
    disputed: list[tuple[str, str]] = []
    for e in by_task.values():
        # A candidate one labeller ticked and another did not is a DISPUTED pair,
        # not a negative. Recording it as "not the same story" would assert a
        # boundary two careful people could not agree on — the coin flip
        # gold_stories.AMBIGUOUS exists to refuse. Excluded from scoring instead.
        definite = [(sel, u, sk) for sel, u, sk in e["answers"] if not u and not sk]
        if len(definite) > 1:
            for cid in e["cands"]:
                votes = {cid in sel for sel, _, _ in definite}
                if len(votes) > 1:
                    disputed.append((e["seed"], cid))
        members, n = merge_votes(e["answers"], e["cands"], min_agree)
        if n == 0:
            continue
        if n == 1:
            singles += 1
        if not members:
            # A real answer: "none of these belong". Kept out of the story block
            # but counted, because a seed nobody linked is a usable negative.
            empties += 1
            continue
        stories.append((e["seed"], members))

    print(f"  batch {batch_key}: {len(by_task)} of {total_tasks} tasks answered")
    print(f"  {len(stories)} stories, {sum(len(m) + 1 for _, m in stories)} events")
    print(f"  {empties} seeds judged to stand alone (usable negatives)")
    if skips:
        print(f"  {skips} response(s) skipped for language — those tasks need a reader")
    print(f"  {len(disputed)} candidate pair(s) DISPUTED — excluded from scoring, not "
          "recorded as negatives")
    if singles:
        print(f"  WARNING: {singles} task(s) rest on ONE labeller — not consensus")
    print()
    for n, (seed, members) in enumerate(sorted(stories), 1):
        print(f'    "corpus-{n:03d}": {json.dumps([seed, *members])},')
    print("\n  # disputed pairs — exclude from scoring")
    for a, b in sorted(disputed):
        print(f'    frozenset({{"{a}", "{b}"}}),')
    print("\n  paste into tools/gold_stories.STORIES, keeping the existing CJP slice")


def compile_gold() -> None:
    """Turn exported decisions into a gold_stories block, ready to paste.

    Ticked events join the seed's story. Unticked candidates become negatives by
    omission — they were SEEN and rejected, which is stronger evidence than never
    having been considered, and it is what makes the sample usable for precision
    as well as recall.
    """
    if not DECISIONS.exists():
        raise SystemExit(f"no {DECISIONS} — export from the review page first")
    snap, _ = _load()
    dec = json.loads(DECISIONS.read_text())
    picked = {seed: list(ids) for seed, ids in dec.get("same", {}).items() if ids}

    lines = []
    for n, (seed, members) in enumerate(sorted(picked.items()), 1):
        title = (snap.titles[snap.index[seed]] or "")[:58].replace('"', "'")
        lines.append(f"    # {title}")
        lines.append(f'    "corpus-{n:03d}": {json.dumps([seed, *members])},')
    print("\n".join(lines))
    print(f"\n  {len(picked)} stories, {sum(len(v) + 1 for v in picked.values())} events")
    print("  paste into tools/gold_stories.STORIES, keeping the existing CJP slice")


_PAGE = """<!doctype html><meta charset=utf-8><title>Prism gold review</title>
<style>
 body{font:15px/1.55 -apple-system,system-ui,sans-serif;max-width:840px;margin:0 auto;padding:24px;background:#0b0b0c;color:#e8e8e8}
 .card{border:1px solid #2a2a2c;border-radius:8px;padding:16px;margin:18px 0;background:#141416}
 h2{font-size:11px;letter-spacing:.09em;text-transform:uppercase;color:#8a8a8f;margin:0 0 10px}
 .sec{color:#d0a24c} .seed{font-size:17px;font-weight:600;margin:0 0 4px}
 .m{font-size:12px;color:#8a8a8f;margin:0;display:block}
 .cands{margin-top:12px}
 .c{display:block;padding:8px;border-radius:6px;cursor:pointer;border:1px solid transparent}
 .c:hover{background:#1c1c1f} .c input{margin-right:9px;vertical-align:middle}
 .c:has(input:checked){background:#16261c;border-color:#2f5d41}
 .cands .m{margin:3px 0 0 25px}
 #bar{position:sticky;top:0;background:#0b0b0ce8;backdrop-filter:blur(6px);padding:12px 0;z-index:9;display:flex;gap:14px;align-items:center}
 button{font:inherit;padding:6px 14px;border-radius:6px;border:1px solid #3a3a3d;background:#1c1c1f;color:#e8e8e8;cursor:pointer}
 #n{color:#8a8a8f;font-size:13px} .lede{color:#8a8a8f;font-size:13px}
</style>
<div id=bar><strong>Prism — story boundaries</strong>
 <button onclick=exp()>Export decisions</button><span id=n></span></div>
<p class=lede>Tick every event belonging to the <b>same unfolding story</b> as the bold headline.
Not the same topic — the same story. Leaving one blank is a real answer: singletons are useful
negatives. Progress saves automatically.</p>
__CARDS__
<script>
const K='prism-gold-v1';
let S=JSON.parse(localStorage.getItem(K)||'{}');
document.querySelectorAll('input').forEach(b=>{
  const k=b.dataset.seed+'|'+b.dataset.id;
  if(S[k])b.checked=true;
  b.addEventListener('change',()=>{S[k]=b.checked;localStorage.setItem(K,JSON.stringify(S));count();});
});
function count(){
  const ticks=Object.values(S).filter(Boolean).length;
  let seeds=0;
  document.querySelectorAll('.card').forEach(c=>{
    if([...c.querySelectorAll('input')].some(i=>i.checked))seeds++;});
  document.getElementById('n').textContent=ticks+' ticked · '+seeds+' seeds with members';
}
function exp(){
  const same={};
  for(const [k,v] of Object.entries(S)){if(!v)continue;const p=k.split('|');(same[p[0]]=same[p[0]]||[]).push(p[1]);}
  const b=new Blob([JSON.stringify({same},null,1)],{type:'application/json'});
  const a=document.createElement('a');a.href=URL.createObjectURL(b);
  a.download='gold_decisions.json';a.click();
}
count();
</script>"""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--propose", action="store_true")
    ap.add_argument("--review", action="store_true")
    ap.add_argument("--compile", action="store_true")
    ap.add_argument("--seeds", type=int, default=123)
    ap.add_argument("--push", metavar="NAME", help="load candidates into a label batch")
    ap.add_argument("--db", metavar="URL", help="target database (default: production)")
    ap.add_argument("--invite", nargs="+", metavar="NAME",
                    help="mint a named credential each, for a batch (needs --batch)")
    ap.add_argument("--batch", metavar="KEY", help="batch key for --invite/--revoke/--status")
    ap.add_argument("--revoke", metavar="NAME", help="withdraw one labeller's credential")
    ap.add_argument("--status", action="store_true", help="who was invited and how far they got")
    ap.add_argument("--agreement", action="store_true",
                    help="do the labellers mean the same thing? pairwise, exact-set")
    ap.add_argument("--compile-batch", metavar="KEY",
                    help="build a gold block from what labellers answered on the page")
    ap.add_argument("--min-agree", type=float, default=0.5,
                    help="fraction of definite answers a candidate needs (default 0.5)")
    ap.add_argument("--site", default="https://www.readprism.news",
                    help="origin to print in invite links")
    a = ap.parse_args()
    if a.propose:
        propose(a.seeds)
    if a.review:
        review()
    if a.push:
        import asyncio

        asyncio.run(push(a.push, a.db))
    if a.invite:
        import asyncio

        if not a.batch:
            raise SystemExit("--invite needs --batch <key>")
        asyncio.run(invite(a.batch, a.invite, a.db, a.site))
    if a.revoke:
        import asyncio

        if not a.batch:
            raise SystemExit("--revoke needs --batch <key>")
        asyncio.run(revoke(a.batch, a.revoke, a.db))
    if a.status:
        import asyncio

        if not a.batch:
            raise SystemExit("--status needs --batch <key>")
        asyncio.run(status(a.batch, a.db))
    if a.agreement:
        import asyncio

        if not a.batch:
            raise SystemExit("--agreement needs --batch <key>")
        asyncio.run(agreement(a.batch, a.db))
    if a.compile:
        compile_gold()
    if a.compile_batch:
        import asyncio

        asyncio.run(compile_from_batch(a.compile_batch, a.db, a.min_agree))
    if not (a.propose or a.review or a.compile or a.push or a.invite
            or a.revoke or a.status or a.compile_batch or a.agreement):
        ap.print_help()


if __name__ == "__main__":
    main()
