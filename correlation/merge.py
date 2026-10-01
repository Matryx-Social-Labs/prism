"""Fold duplicate records into the record they copy — the verified tier's backlog.

Before the verified tier went live (2026-09-27 17:12 UTC) it ran in shadow: for
each article every other tier refused, Jev judged it against up to five
existing records and the answer went into `event_match_verdicts` — and the
article founded its own record anyway. Where Jev said >= 0.85 that new record is
a copy (25 of 25 sampled were right). This folds each copy into the record it
was judged against:

- SURVIVOR = the existing record the verdict named, whose founding headline Jev
  read. ABSORBED = the record the judged article founded.
- STAR, NEVER A CHAIN. If the survivor is itself a copy, the absorbed record goes
  to that record's survivor, so every `merged_into` names a record that is not
  merged. Pairs are never linked transitively the other way (union-find chained a
  week of Trump–Xi coverage into one 46-event group, docs/CANONICALIZATION.md).
- A copy is folded only when every article in it was judged the same happening:
  its founder against the survivor, or a later member the live tier attached
  against the copy's own founder. A copy holding anything else (an article that
  joined on shared actors, say) is reported, not merged — moving it would move
  an article nobody judged.
- Members and every row that points at the copy move to the survivor (a row the
  survivor already has a twin of is dropped); the survivor's projection is
  rebuilt by the consumer's own rebuild in the same transaction; the absorbed row
  stays with `merged_into` set. Derived per-record analysis (perspectives,
  impacts) is dropped and the survivor is queued for the analysis pass.

One transaction per merge, under the correlation consumer's match-or-create
lock, re-checked inside it — so a run can stop anywhere and simply be re-run.

RECORD TO RECORD (plan_events). The shadow verdicts reach only a copy whose
every article was judged, so a duplicate built from several articles stayed
separate: the Parvesh Verma slap was six records (7, 4, 3, 2, 1… outlets) after
the first run. plan_events judges the records themselves, the verified tier's
way — candidates by the FOUNDERS' gists, Jev on each record's founding headline +
summary — and groups them into stars (`stars`). A record so judged moves whole:
its other members were filed by the cascade as its own happening.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.db import session_scope
from common.logging import get_logger
from common.outlets import RAW_RECORD_FEEDS
from correlation.clustering import GIST_CANDIDATES, _scale
from correlation.consumer import _rebuild_projection, mark_event_dirty
from correlation.verify import Candidate, event_blocks, judge, record

logger = get_logger(__name__)

# correlation.consumer._attach's lock, held for a whole match-or-create: taken
# for a whole merge too, an article can never attach to a record mid-fold.
MATCH_OR_CREATE_LOCK = "SELECT pg_advisory_xact_lock(hashtext('correlation.match_or_create'))"

# Tables keyed on (event_id, these columns): a copy's row moves unless the
# survivor already holds its twin, in which case the survivor's is kept.
KEYED = {
    "event_entities": ("entity_id",),
    "lens_unlocks": ("user_id", "lens"),  # paid: a reader keeps every lens they unlocked
    "event_story": ("run_id",),
    "claim_verdicts": ("speaker_key",),
    "event_clips": ("window_id",),
    "clip_verdicts": ("window_id",),
    "event_x_posts": ("post_id",),
    "x_post_verdicts": ("post_id",),
    "story_verdicts": ("story_id",),
}
# Left on the absorbed row on purpose. The verdicts are the evidence for the
# merge; a labelling task is history; a veto verdict is a cache keyed on a
# story's signature. (event_revisions and event_corrections, which carry no
# foreign key, stay too: they are the absorbed record's own history.)
LEFT = {"event_match_verdicts", "label_tasks"}
HANDLED_TABLES = (
    set(KEYED) | LEFT
    | {"event_memberships", "agent_sessions", "event_links", "perspectives", "impacts", "stories", "story_events"}
)


@dataclass(frozen=True)
class Merge:
    absorbed: uuid.UUID
    survivor: uuid.UUID
    noul: float  # Jev's answer for the absorbed record's founder
    via: uuid.UUID | None  # the record Jev named, when the survivor was reached through it
    whole: bool = False  # judged record to record (stars): the copy moves with every member it holds


@dataclass(frozen=True)
class Skip:
    absorbed: uuid.UUID
    candidate: uuid.UUID
    noul: float
    reason: str


# The merge floor, apart from the live attach floor (prism_event_verify_min):
# the 2026-09-27 merge ran at 0.87 by setting PRISM_EVENT_VERIFY_MIN, which would
# have raised the live tier's floor too. tools/merge_duplicates --min sets this.
MERGE_MIN: float | None = None


def _floor() -> float:
    return MERGE_MIN if MERGE_MIN is not None else get_settings().prism_event_verify_min


async def _uncovered(session: AsyncSession, pairs: list[tuple[uuid.UUID, uuid.UUID]]) -> dict[uuid.UUID, list[str]]:
    """Per absorbed record, the match types of members nobody judged the same
    happening as the survivor or as the absorbed record's own founder."""
    if not pairs:
        return {}
    rows = (
        await session.execute(
            text(
                """
                SELECT m.event_id, m.match_type
                FROM unnest(CAST(:a AS uuid[]), CAST(:c AS uuid[])) AS p(absorbed, candidate)
                JOIN event_memberships m ON m.event_id = p.absorbed
                WHERE NOT EXISTS (
                    SELECT 1 FROM event_match_verdicts v
                    WHERE v.article_id = m.article_id AND v.noul >= :floor
                      AND v.event_id IN (p.absorbed, p.candidate)
                )
                ORDER BY m.event_id, m.match_type
                """
            ),
            {"a": [str(a) for a, _ in pairs], "c": [str(c) for _, c in pairs], "floor": _floor()},
        )
    ).all()
    out: dict[uuid.UUID, list[str]] = {}
    for event_id, match_type in rows:
        out.setdefault(event_id, []).append(match_type)
    return out


async def plan(session: AsyncSession) -> tuple[list[Merge], list[Skip]]:
    """Every copy the shadow verdicts name, resolved to its final survivor, most
    certain first; and every copy that cannot be folded, with why."""
    rows = (
        await session.execute(
            text(
                """
                -- The judged article still FOUNDS the record it sits in: after a
                -- merge its membership reads 'merged', so a done pair drops out.
                SELECT DISTINCT ON (v.article_id) m.event_id AS absorbed, v.event_id AS candidate, v.noul
                FROM event_match_verdicts v
                JOIN event_memberships m ON m.article_id = v.article_id AND m.match_type = 'new_event'
                JOIN events a ON a.id = m.event_id AND a.merged_into IS NULL
                WHERE v.mode = 'shadow' AND v.noul >= :floor AND v.event_id <> m.event_id
                ORDER BY v.article_id, v.noul DESC, v.event_id
                """
            ),
            {"floor": _floor()},
        )
    ).all()
    judged = {r.absorbed: (r.candidate, float(r.noul)) for r in rows}
    uncovered = await _uncovered(session, [(a, c) for a, (c, _) in judged.items()])
    earlier = dict(
        (
            await session.execute(
                text("SELECT id, merged_into FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(c) for c, _ in judged.values()]},
            )
        ).all()
    )
    skips: list[Skip] = []
    target: dict[uuid.UUID, uuid.UUID] = {}
    for a, (c, p) in judged.items():
        if a in uncovered:
            n = len(uncovered[a])
            kinds = ", ".join(sorted({f"{t} x{uncovered[a].count(t)}" for t in uncovered[a]}))
            skips.append(Skip(a, c, p, f"{n} member(s) not judged the same happening ({kinds})"))
        elif c not in earlier:
            skips.append(Skip(a, c, p, "candidate record no longer exists"))
        else:
            target[a] = c

    def root(e: uuid.UUID) -> uuid.UUID | None:
        seen = {e}
        while (nxt := target.get(e) or earlier.get(e)) is not None:
            if nxt in seen:
                return None  # a cycle; verdicts point back in time, so this is corruption
            seen.add(nxt)
            e = nxt
        return e

    merges: list[Merge] = []
    for a, c in target.items():
        r = root(a)
        if r is None:
            skips.append(Skip(a, c, judged[a][1], "cycle in the verdicts"))
        else:
            merges.append(Merge(absorbed=a, survivor=r, noul=judged[a][1], via=c if r != c else None))
    merges.sort(key=lambda m: (-m.noul, str(m.absorbed)))
    return merges, skips


async def apply(m: Merge) -> bool:
    """Fold one copy into its survivor, in one transaction. False when there is
    nothing to do: already merged, either record gone or itself merged, or (for a
    copy found by its articles' verdicts) the copy has gained an article nobody
    judged since the plan was made."""
    ids = {"a": str(m.absorbed), "s": str(m.survivor)}
    async with session_scope() as s:
        await s.execute(text(MATCH_OR_CREATE_LOCK))
        state = dict(
            (
                await s.execute(
                    text("SELECT id, merged_into FROM events WHERE id IN (:a, :s) FOR UPDATE"), ids
                )
            ).all()
        )
        if len(state) != 2 or any(state.values()):
            return False
        if not m.whole and await _uncovered(s, [(m.absorbed, m.via or m.survivor)]):
            return False
        # The fold keeps the newest news on the survivor's clock, not the
        # merge's: the rebuild below stamps now(), which would lift every
        # survivor of a backlog run to the top of the latest-first lists.
        last: datetime = (
            await s.execute(
                text("SELECT max(last_updated_at) FROM events WHERE id IN (:a, :s)"), ids
            )
        ).scalar_one()

        await s.execute(
            text(
                """
                UPDATE event_memberships
                SET event_id = :s, is_survivor = false,
                    match_score = CASE WHEN match_type = 'new_event' THEN :p ELSE match_score END,
                    match_type = CASE WHEN match_type = 'new_event' THEN 'merged' ELSE match_type END
                WHERE event_id = :a
                """
            ),
            {**ids, "p": m.noul},
        )
        for table, keys in KEYED.items():
            twin = " AND ".join(f"x.{k} = t.{k}" for k in keys)
            await s.execute(
                text(
                    f"UPDATE {table} t SET event_id = :s WHERE t.event_id = :a "
                    f"AND NOT EXISTS (SELECT 1 FROM {table} x WHERE x.event_id = :s AND {twin})"
                ),
                ids,
            )
            await s.execute(text(f"DELETE FROM {table} WHERE event_id = :a"), ids)
        await s.execute(text("UPDATE agent_sessions SET event_id = :s WHERE event_id = :a"), ids)
        # Thread edges: re-anchored on the survivor, except one between the two
        # copies (it would be a self-loop) or one the survivor already has.
        for col, other in (("from_event_id", "to_event_id"), ("to_event_id", "from_event_id")):
            await s.execute(
                text(
                    f"UPDATE event_links t SET {col} = :s WHERE t.{col} = :a AND t.{other} <> :s "
                    f"AND NOT EXISTS (SELECT 1 FROM event_links x WHERE x.{col} = :s AND x.{other} = t.{other})"
                ),
                ids,
            )
        await s.execute(text("DELETE FROM event_links WHERE :a IN (from_event_id, to_event_id)"), ids)
        await s.execute(text("DELETE FROM perspectives WHERE event_id = :a"), ids)
        await s.execute(text("DELETE FROM impacts WHERE event_id = :a"), ids)
        # One story per record: the copy's place moves to the survivor unless the
        # survivor has its own; a story founded on the copy is re-anchored.
        await s.execute(text("UPDATE story_events SET event_id = :s WHERE event_id = :a "
                             "AND NOT EXISTS (SELECT 1 FROM story_events x WHERE x.event_id = :s)"), ids)
        await s.execute(text("DELETE FROM story_events WHERE event_id = :a"), ids)
        await s.execute(text("UPDATE stories SET anchor_event_id = :s WHERE anchor_event_id = :a"), ids)
        await _move_story_members(s, m)

        # As an attach would: the survivor takes the copy's photo if it had
        # none. Its sector and states are re-read from all its members by the
        # rebuild below (the classifier's majority, never a union).
        await s.execute(
            text("UPDATE events sv SET image_url = COALESCE(sv.image_url, ab.image_url) "
                 "FROM events ab WHERE sv.id = :s AND ab.id = :a"),
            ids,
        )
        await s.execute(text("UPDATE events SET merged_into = :s WHERE id = :a OR merged_into = :a"), ids)
        await _rebuild_projection(m.survivor, session=s)
        await s.flush()
        await s.execute(text("UPDATE events SET last_updated_at = :t WHERE id = :s"), {**ids, "t": last})
    await mark_event_dirty(m.survivor)
    return True


async def _move_story_members(s: AsyncSession, m: Merge) -> None:
    """Trending stories name their members in a JSON list: the copy becomes the
    survivor there, once, in the copy's place."""
    rows = (
        await s.execute(
            text(
                "SELECT id, member_event_ids, hero_event_id FROM stories "
                "WHERE member_event_ids @> CAST(:m AS jsonb) OR hero_event_id = :a"
            ),
            {"m": json.dumps([str(m.absorbed)]), "a": str(m.absorbed)},
        )
    ).all()
    for sid, members, hero in rows:
        moved = list(dict.fromkeys(str(m.survivor) if x == str(m.absorbed) else x for x in members))
        await s.execute(
            text("UPDATE stories SET member_event_ids = CAST(:m AS jsonb), hero_event_id = :h WHERE id = :i"),
            {"m": json.dumps(moved), "h": str(m.survivor) if hero == m.absorbed else hero, "i": str(sid)},
        )


# ── Record to record ────────────────────────────────────────────────────────

PAIR_WINDOW = timedelta(hours=72)  # never a merge between records first seen further apart
PAIR_MODE = "pair"  # event_match_verdicts.mode: article = one record's founder, event = the other record
PAIR_BUDGET_USD = 1.0  # a run stops asking Jev here; a week of production was ~$0.40 (audit_event_dups)
PAIR_CONCURRENCY = 8


@dataclass(frozen=True)
class Record:
    id: uuid.UUID
    founder: uuid.UUID  # the founding article: its gist finds candidates, the verdict row is keyed on it
    publishers: int
    first_seen: datetime


def _rank(r: Record) -> tuple:
    """Survivor order: the most publishers, then the earliest."""
    return (-r.publishers, r.first_seen, str(r.id))


def stars(
    records: dict[uuid.UUID, Record], verdicts: dict[frozenset[uuid.UUID], float]
) -> tuple[list[Merge], set[frozenset[uuid.UUID]]]:
    """Duplicate records grouped into STARS, never chains. Taken in survivor
    order, each record not yet taken is a survivor, and it takes every record Jev
    linked to it or to one of its takers — but a record joins only on its OWN
    verdict against the survivor (>= the floor, first seen within PAIR_WINDOW of
    it). A record reached through another but never judged against the survivor
    comes back in `wanted`: judge those pairs and call again. Union-find over the
    same verdicts chained a week of Trump–Xi coverage into one 46-event group."""
    floor = _floor()
    linked: dict[uuid.UUID, set[uuid.UUID]] = {}
    for pair, p in verdicts.items():
        if p >= floor and pair.issubset(records):
            x, y = pair
            linked.setdefault(x, set()).add(y)
            linked.setdefault(y, set()).add(x)
    taken: set[uuid.UUID] = set()
    merges: list[Merge] = []
    wanted: set[frozenset[uuid.UUID]] = set()
    for s in sorted(records.values(), key=_rank):
        if s.id in taken:
            continue
        taken.add(s.id)
        reach = [s.id]
        while reach:
            for y in sorted(linked.get(reach.pop(), ()), key=str):
                if y in taken or abs(records[y].first_seen - s.first_seen) > PAIR_WINDOW:
                    continue
                p = verdicts.get(frozenset((y, s.id)))
                if p is None:
                    wanted.add(frozenset((y, s.id)))
                elif p >= floor:
                    taken.add(y)
                    reach.append(y)
                    merges.append(Merge(absorbed=y, survivor=s.id, noul=p, via=None, whole=True))
    return merges, wanted


@dataclass
class PairPlan:
    merges: list[Merge] = field(default_factory=list)
    # Jev's answers this run, one entry per call: (asking founder, [(candidate, noul)], model).
    judged: list[tuple[uuid.UUID, list[tuple[Candidate, float]], str]] = field(default_factory=list)
    records: int = 0
    candidates: int = 0  # gist pairs
    reused: int = 0  # of those, answered before (any mode)
    calls: int = 0
    pairs: int = 0  # answered this run, extra direct pairs included
    failed: int = 0  # pairs whose call failed or timed out: not merged this run
    unasked: int = 0  # pairs left at the budget
    cost: float = 0.0


async def _served(s: AsyncSession, days: int) -> tuple[dict[uuid.UUID, Record], np.ndarray]:
    """Unmerged records with a news source, first seen in the last `days`, and
    their founders' gists (unit rows, in the dict's order)."""
    rows = (
        await s.execute(
            text(
                """
                SELECT DISTINCT ON (e.id) e.id, m.article_id AS founder, e.first_seen_at,
                       COALESCE((e.projection->>'source_count')::int, 0) AS publishers,
                       a.gist_embedding::float4[] AS gist
                FROM events e
                JOIN event_memberships m ON m.event_id = e.id AND m.match_type = 'new_event'
                JOIN articles a ON a.id = m.article_id AND a.gist_embedding IS NOT NULL
                WHERE e.merged_into IS NULL AND e.first_seen_at > now() - make_interval(days => :days)
                  AND COALESCE(jsonb_array_length(e.projection->'source_slugs'), 0) > 0
                  AND NOT (e.projection->'source_slugs') <@ CAST(:raw_feeds AS jsonb)
                ORDER BY e.id, m.article_id
                """
            ),
            {"days": days, "raw_feeds": json.dumps(sorted(RAW_RECORD_FEEDS))},
        )
    ).all()
    records = {r.id: Record(r.id, r.founder, int(r.publishers), r.first_seen_at) for r in rows}
    if not rows:
        return records, np.zeros((0, 1), dtype="float32")
    vecs = np.asarray([r.gist for r in rows], dtype="float32")
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True) + 1e-12
    return records, vecs


def _near(records: list[Record], vecs: np.ndarray) -> dict[frozenset[uuid.UUID], float]:
    """Each record's nearest GIST_CANDIDATES others first seen within the window
    and inside the verified tier's gist floor: pair -> cosine distance."""
    max_dist = _scale().get("gist_candidate")
    if max_dist is None or len(records) < 2:
        return {}
    t = np.array([r.first_seen.timestamp() for r in records])
    out: dict[frozenset[uuid.UUID], float] = {}
    step = 1024  # ponytail: dense blocks, O(n^2); a pgvector index if the window grows past ~100k records
    for i0 in range(0, len(records), step):
        rows = np.arange(i0, min(i0 + step, len(records)))
        sims = vecs[rows] @ vecs.T
        sims[np.abs(t[rows, None] - t[None, :]) > PAIR_WINDOW.total_seconds()] = -1.0
        sims[rows - i0, rows] = -1.0
        for i, js in zip(rows, np.argsort(-sims, axis=1)[:, :GIST_CANDIDATES], strict=True):
            for j in js:
                if (d := 1.0 - float(sims[i - i0, j])) <= max_dist:
                    out[frozenset((records[i].id, records[j].id))] = d
    return out


async def _known(s: AsyncSession, records: dict[uuid.UUID, Record]) -> dict[frozenset[uuid.UUID], float]:
    """Answers already on file between two of these records, in any mode: one
    record's founder judged against the other's founding headline and summary."""
    rows = (
        await s.execute(
            text(
                """
                SELECT m.event_id AS x, v.event_id AS y, v.noul
                FROM event_match_verdicts v
                JOIN event_memberships m ON m.article_id = v.article_id AND m.match_type = 'new_event'
                WHERE m.event_id = ANY(CAST(:ids AS uuid[])) AND v.event_id = ANY(CAST(:ids AS uuid[]))
                  AND v.event_id <> m.event_id
                """
            ),
            {"ids": [str(i) for i in records]},
        )
    ).all()
    out: dict[frozenset[uuid.UUID], float] = {}
    for x, y, p in rows:
        k = frozenset((x, y))
        out[k] = min(out.get(k, 1.0), float(p))  # asked both ways: the doubtful answer counts
    return out


async def _ask(todo, records, blocks, dist, plan: PairPlan, budget: float) -> dict[frozenset[uuid.UUID], float]:
    """Jev on each pair, batched as the live tier batches: the lower-ranked
    record asks, against up to GIST_CANDIDATES higher-ranked records a call."""
    asks: dict[uuid.UUID, list[uuid.UUID]] = {}
    for pair in todo:
        hi, lo = sorted(pair, key=lambda i: _rank(records[i]))
        asks.setdefault(lo, []).append(hi)
    got: dict[frozenset[uuid.UUID], float] = {}
    sem = asyncio.Semaphore(PAIR_CONCURRENCY)

    async def one(lo: uuid.UUID, his: list[uuid.UUID]) -> None:
        async with sem:
            if plan.cost >= budget:
                plan.unasked += len(his)
                return
            cands = [Candidate(event_id=h, distance=dist(lo, h)) for h in his]
            try:
                scored, model, cost = await judge(
                    article_id=records[lo].founder, block=blocks[lo], candidates=cands, blocks=blocks
                )
            except Exception as exc:  # noqa: BLE001 — an unjudged pair is simply not merged this run
                logger.warning("event_pair_judge_failed", record=str(lo), error=str(exc)[:160])
                plan.failed += len(his)
                return
        plan.calls += 1
        plan.pairs += len(scored)
        plan.cost += cost
        plan.judged.append((records[lo].founder, scored, model))
        for c, p in scored:
            got[frozenset((lo, c.event_id))] = p

    batches = []
    for lo, his in asks.items():
        his = sorted(his, key=str)
        batches += [one(lo, his[i : i + GIST_CANDIDATES]) for i in range(0, len(his), GIST_CANDIDATES)]
    await asyncio.gather(*batches)
    return got


async def plan_events(*, days: int = 7, budget: float = PAIR_BUDGET_USD) -> PairPlan:
    """Every duplicate record first seen in the last `days`, as star merges, most
    certain first. Asks Jev about every candidate pair not answered before, then
    about each pair `stars` wants judged directly, until none is left. Reads in a
    READ ONLY transaction and writes nothing: this run's answers come back in
    `judged` for record_pairs() to keep."""
    async with session_scope() as s:
        await s.execute(text("SET TRANSACTION READ ONLY"))
        await s.execute(text("SET LOCAL statement_timeout = '120s'"))
        records, vecs = await _served(s, days)
        verdicts = await _known(s, records)
        blocks = await event_blocks(s, list(records))
    order = list(records.values())
    row = {r.id: i for i, r in enumerate(order)}
    near = _near(order, vecs)
    plan = PairPlan(records=len(records), candidates=len(near), reused=len(near.keys() & verdicts.keys()))

    def dist(a: uuid.UUID, b: uuid.UUID) -> float:
        k = frozenset((a, b))
        return near[k] if k in near else 1.0 - float(vecs[row[a]] @ vecs[row[b]])

    todo, asked = set(near) - set(verdicts), set()
    while True:
        if todo:
            verdicts |= await _ask(todo, records, blocks, dist, plan, budget)
            asked |= todo
        merges, wanted = stars(records, verdicts)
        todo = wanted - asked
        if not todo:
            break
    plan.merges = sorted(merges, key=lambda m: (-m.noul, str(m.absorbed)))
    return plan


async def record_pairs(judged: list[tuple[uuid.UUID, list[tuple[Candidate, float]], str]]) -> None:
    """Keep a run's answers (mode 'pair'), so the next run pays for none of them
    and every merge can be traced to the verdict that made it."""
    async with session_scope() as s:
        for founder, scored, model in judged:
            await record(s, article_id=founder, scored=scored, model=model, mode=PAIR_MODE)
