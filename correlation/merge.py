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
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.db import session_scope
from correlation.consumer import _rebuild_projection, mark_event_dirty

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
}
# Left on the absorbed row on purpose. The verdicts are the evidence for the
# merge; a labelling task is history; a veto verdict is a cache keyed on a
# story's signature. (event_revisions and event_corrections, which carry no
# foreign key, stay too: they are the absorbed record's own history.)
LEFT = {"event_match_verdicts", "label_tasks"}
HANDLED_TABLES = (
    set(KEYED) | LEFT
    | {"event_memberships", "agent_sessions", "event_links", "perspectives", "impacts"}
)


@dataclass(frozen=True)
class Merge:
    absorbed: uuid.UUID
    survivor: uuid.UUID
    noul: float  # Jev's answer for the absorbed record's founder
    via: uuid.UUID | None  # the record Jev named, when the survivor was reached through it


@dataclass(frozen=True)
class Skip:
    absorbed: uuid.UUID
    candidate: uuid.UUID
    noul: float
    reason: str


def _floor() -> float:
    return get_settings().prism_event_verify_min


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
    nothing to do: already merged, either record gone or itself merged, or the
    copy has gained an article nobody judged since the plan was made."""
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
        if await _uncovered(s, [(m.absorbed, m.via or m.survivor)]):
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
