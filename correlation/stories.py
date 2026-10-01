"""Stories that persist: a record joins one story at birth, on the judge's word.

WHY NOT A PARTITION. The story layer was a global Leiden partition rebuilt every
15 minutes and kept only while a story trended. CPM over a mutual-kNN graph
(k=4) caps a community near 25 records, so a developing story of 100 shatters:
on 2026-10-01 the Iran war's 360 records sat in 198 groups and Flydubai's 102 in
35. Retrieval was never the limit — a story sibling is among a record's four
nearest neighbours 97-100% of the time — the density cut was. A record needs
one confirmed neighbour in its story, not a dense community.

HOW. The stories of the record's nearest earlier records by founder gist, and
the story of any record the verifier linked it to as a later development, are
proposed (at most CANDIDATES). One Jev call asks, per story, whether the record
is part of it — judged against the story's founding report (a running story's
scope instead), its latest report and its two members nearest the record — and
what kind of development it is (verify.FACETS). The best story at or above
prism_story_min takes it; otherwise the record founds a story. Star to the
story, never record to record, so nothing chains. Prototype on 12,941 records
(24 Sep-1 Oct): Flydubai 13% -> 92% in one story; precision 0.92-0.97 on 60 read.

A failed or slow judge founds a story, as a failed record judgement founds a
record: the cheaper mistake, merged later.
"""

from __future__ import annotations

import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.decisions import Choice, ChoiceAnswer, Noul, NoulAnswer, decide
from common.logging import get_logger
from correlation.trending import _label, story_slug
from correlation.verify import FACETS, PART_OF_STORY, VERIFY_TIMEOUT_S, ann_scan

logger = get_logger(__name__)

NEIGHBOUR_DIST = 0.11  # founder-gist cosine distance (mE5) for a record to propose its story
CANDIDATES = 3
WINDOW_DAYS = 14
NEAR_MEMBERS = 2
ANN = 200  # nearest in-window founder gists the index scan returns before grouping by story


def _vec(v) -> str:
    return "[" + ",".join(f"{float(x):.7f}" for x in v) + "]"


async def _record(session: AsyncSession, event_id: uuid.UUID):
    return (
        await session.execute(
            text(
                """
                SELECT e.id, e.title, e.summary, e.merged_into,
                       coalesce(e.first_published_at, e.first_seen_at) AS at,
                       (SELECT a.gist_embedding::text FROM event_memberships m JOIN articles a ON a.id = m.article_id
                        WHERE m.event_id = e.id AND m.match_type = 'new_event' LIMIT 1) AS gist,
                       EXISTS (SELECT 1 FROM story_events se WHERE se.event_id = e.id) AS placed
                FROM events e WHERE e.id = :e
                """
            ),
            {"e": str(event_id)},
        )
    ).one_or_none()


async def _candidates(session: AsyncSession, rec) -> list[tuple[uuid.UUID, float | None]]:
    """(story, nearest member's gist distance) — a verified follow-up's story first."""
    found: dict[uuid.UUID, float | None] = {}
    linked = (
        await session.execute(
            text(
                """
                SELECT DISTINCT se.story_id FROM event_links l
                JOIN story_events se ON se.event_id = CASE WHEN l.to_event_id = :e THEN l.from_event_id ELSE l.to_event_id END
                JOIN stories s ON s.id = se.story_id AND s.merged_into IS NULL
                WHERE (l.to_event_id = :e OR l.from_event_id = :e) AND l.method = 'verified' AND l.relation = 'leads_to'
                """
            ),
            {"e": str(rec.id)},
        )
    ).scalars().all()
    for sid in linked:
        found[sid] = None
    if rec.gist is not None:
        await ann_scan(session)  # the window is applied inside the HNSW scan
        rows = (
            await session.execute(
                text(
                    f"""
                    WITH near AS MATERIALIZED (
                        SELECT a.id, a.gist_embedding <=> CAST(:vec AS vector) AS d
                        FROM articles a
                        WHERE a.gist_embedding IS NOT NULL
                          AND a.created_at >= CAST(:at AS timestamptz) - interval '{WINDOW_DAYS + 1} days'
                        ORDER BY a.gist_embedding <=> CAST(:vec AS vector)
                        LIMIT :ann
                    )
                    SELECT se.story_id, min(near.d) AS d
                    FROM near
                    JOIN event_memberships m ON m.article_id = near.id AND m.match_type = 'new_event'
                    JOIN events e ON e.id = m.event_id AND e.merged_into IS NULL
                    JOIN story_events se ON se.event_id = e.id
                    JOIN stories s ON s.id = se.story_id AND s.merged_into IS NULL
                    WHERE near.d <= :maxd
                      AND coalesce(e.first_published_at, e.first_seen_at)
                          BETWEEN CAST(:at AS timestamptz) - interval '{WINDOW_DAYS} days'
                              AND CAST(:at AS timestamptz) + interval '1 hour'
                    GROUP BY se.story_id
                    ORDER BY d, se.story_id
                    LIMIT :k
                    """
                ),
                {"vec": rec.gist, "at": rec.at, "maxd": NEIGHBOUR_DIST, "k": CANDIDATES, "ann": ANN},
            )
        ).all()
        for r in rows:
            found.setdefault(r.story_id, float(r.d))
    return list(found.items())[:CANDIDATES]


def _report_block(rec) -> str:
    return f"First reported {rec.at:%Y-%m-%d %H:%M}.\nHeadline: {rec.title}\nSummary: {(rec.summary or '')[:400]}"


async def _story_block(session: AsyncSession, story_id: uuid.UUID, rec) -> str:
    """The story as the judge reads it: its founding report (a running story's
    scope), its latest report, and the two members nearest the record."""
    s = (
        await session.execute(
            text(
                """
                SELECT s.scope, a.title, a.summary, coalesce(a.first_published_at, a.first_seen_at) AS at,
                       (SELECT count(*) FROM story_events x WHERE x.story_id = s.id) AS n,
                       (SELECT e.title FROM story_events x JOIN events e ON e.id = x.event_id
                        WHERE x.story_id = s.id AND e.merged_into IS NULL
                        ORDER BY coalesce(e.first_published_at, e.first_seen_at) DESC LIMIT 1) AS latest
                FROM stories s
                LEFT JOIN events a ON a.id = s.anchor_event_id
                WHERE s.id = :s
                """
            ),
            {"s": str(story_id)},
        )
    ).one()
    near: list[str] = []
    if rec.gist is not None:
        near = list(
            (
                await session.execute(
                    text(
                        """
                        SELECT e.title FROM story_events x
                        JOIN events e ON e.id = x.event_id AND e.merged_into IS NULL
                        JOIN stories s ON s.id = x.story_id
                        JOIN event_memberships m ON m.event_id = e.id AND m.match_type = 'new_event'
                        JOIN articles a ON a.id = m.article_id
                        WHERE x.story_id = :s AND e.id IS DISTINCT FROM s.anchor_event_id AND a.gist_embedding IS NOT NULL
                        ORDER BY a.gist_embedding <=> CAST(:vec AS vector) LIMIT :n
                        """
                    ),
                    {"s": str(story_id), "vec": rec.gist, "n": NEAR_MEMBERS},
                )
            ).scalars().all()
        )
    if s.scope:
        lines = [f"Running story: {s.scope}"]
    else:
        lines = [f"Story first reported {s.at:%Y-%m-%d %H:%M}, {s.n} records so far.",
                 f"Founding report: {s.title}. {(s.summary or '')[:300]}"]
    if s.latest and s.latest != s.title:
        lines.append(f"Latest report: {s.latest}")
    lines += [f"Also in this story: {t}" for t in near if t not in (s.title, s.latest)]
    return "\n".join(lines)


async def _judge(rec, blocks: list[str]) -> tuple[list[tuple[float, str]], str]:
    """(part-of-story, facet) per story block, one Jev call. Network only."""
    state = {"REPORT": _report_block(rec), **{f"STORY_{k}": b for k, b in enumerate(blocks, 1)}}
    questions: dict = {}
    for k in range(1, len(blocks) + 1):
        questions[f"part_{k}"] = Noul(instructions=PART_OF_STORY.format(a="REPORT", b=f"STORY_{k}"))
        questions[f"facet_{k}"] = Choice(instructions=f"What kind of development in STORY_{k} does REPORT report?",
                                         criteria=FACETS)
    d = await asyncio.wait_for(decide(state, questions, trace_name="story-assign",
                                      metadata={"stage": "stories", "event_id": str(rec.id)}), VERIFY_TIMEOUT_S)
    out = []
    for k in range(1, len(blocks) + 1):
        part, facet = d.answers[f"part_{k}"], d.answers[f"facet_{k}"]
        assert isinstance(part, NoulAnswer) and isinstance(facet, ChoiceAnswer)
        out.append((part.noul, facet.choice if facet.choice in FACETS else "event"))
    return out, d.model or get_settings().prism_model_decide


async def _found(session: AsyncSession, rec, status: str) -> uuid.UUID:
    sid = uuid.uuid4()
    label = _label([], rec.title, None)
    await session.execute(
        text(
            """
            INSERT INTO stories (id, slug, label, "cast", member_event_ids, hero_event_id, anchor_event_id,
                                 source_count, velocity, status, first_seen_at, last_updated_at)
            VALUES (:id, :slug, :label, '[]'::jsonb, CAST(:members AS jsonb), :e, :e, 0, 0, :status, now(), now())
            """
        ),
        # A shadow story keeps member_event_ids empty: search and the record page
        # find a record's story through it, and a shadow story is never served.
        {"id": str(sid), "slug": story_slug(label, sid), "label": label,
         "members": "[]" if status == "shadow" else f'["{rec.id}"]', "e": str(rec.id), "status": status},
    )
    await session.execute(text("INSERT INTO story_events (event_id, story_id, facet) VALUES (:e, :s, 'event')"),
                          {"e": str(rec.id), "s": str(sid)})
    return sid


async def _join(session: AsyncSession, rec, story_id: uuid.UUID, noul: float, facet: str) -> None:
    await session.execute(text("INSERT INTO story_events (event_id, story_id, noul, facet) VALUES (:e, :s, :n, :f)"),
                          {"e": str(rec.id), "s": str(story_id), "n": noul, "f": facet})
    await session.execute(
        text("UPDATE stories SET member_event_ids = CASE WHEN status = 'shadow' THEN member_event_ids "
             "ELSE member_event_ids || CAST(:m AS jsonb) END, last_updated_at = now() WHERE id = :s"),
        {"m": f'["{rec.id}"]', "s": str(story_id)},
    )


async def assign_story(session: AsyncSession, event_id: uuid.UUID) -> uuid.UUID | None:
    """Place one record in exactly one story (prism_stories shadow|live). Returns
    the story, or None when off, merged away or already placed. Serialised: two
    records of one new story arriving together must not found two stories."""
    settings = get_settings()
    mode = settings.prism_stories
    if mode not in ("shadow", "live"):
        return None
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('stories.assign'))"))
    rec = await _record(session, event_id)
    if rec is None or rec.merged_into is not None or rec.placed:
        return None
    candidates = await _candidates(session, rec)
    if candidates:
        blocks = [await _story_block(session, sid, rec) for sid, _ in candidates]
        try:
            answers, model = await _judge(rec, blocks)
        except Exception as exc:  # noqa: BLE001 — an unjudged record founds its own story; the merge pass folds it later
            logger.warning("story_assign_failed", event_id=str(event_id), error=str(exc)[:160])
        else:
            await session.execute(
                text("INSERT INTO story_verdicts (event_id, story_id, noul, facet, distance, model) "
                     "VALUES (:e, :s, :n, :f, :d, :m) ON CONFLICT (event_id, story_id) DO UPDATE "
                     "SET noul = EXCLUDED.noul, facet = EXCLUDED.facet, model = EXCLUDED.model"),
                [{"e": str(event_id), "s": str(sid), "n": n, "f": f, "d": d, "m": model}
                 for (sid, d), (n, f) in zip(candidates, answers, strict=True)],
            )
            (sid, _), (noul, facet) = max(zip(candidates, answers, strict=True), key=lambda c: c[1][0])
            if noul >= settings.prism_story_min:
                await _join(session, rec, sid, noul, facet)
                return sid
    return await _found(session, rec, "shadow" if mode == "shadow" else "active")


async def create_running_story(session: AsyncSession, *, title: str, scope: str,
                               anchor_event_id: uuid.UUID) -> uuid.UUID:
    """A founder-created story for an ongoing war, dispute, campaign or
    tournament: judged on its scope line, not on a founding report."""
    sid = uuid.uuid4()
    status = "active" if get_settings().prism_stories == "live" else "shadow"
    await session.execute(
        text(
            """
            INSERT INTO stories (id, slug, label, "cast", member_event_ids, hero_event_id, anchor_event_id, scope,
                                 source_count, velocity, status, first_seen_at, last_updated_at)
            VALUES (:id, :slug, :label, '[]'::jsonb, '[]'::jsonb, :e, :e, :scope, 0, 0, :status, now(), now())
            """
        ),
        {"id": str(sid), "slug": story_slug(title, sid), "label": title, "e": str(anchor_event_id),
         "scope": scope, "status": status},
    )
    return sid


async def absorb(session: AsyncSession, into: uuid.UUID, story_id: uuid.UUID) -> int:
    """Move every record of `story_id` into `into`; the absorbed story redirects
    there (merged_into; dormant, as a trending merge, unless it is a shadow story,
    which stays unserved). Returns records moved."""
    moved = (
        await session.execute(text("UPDATE story_events SET story_id = :into WHERE story_id = :s"),
                              {"into": str(into), "s": str(story_id)})
    ).rowcount
    await session.execute(
        text(
            """
            UPDATE stories t SET member_event_ids = CASE WHEN t.status = 'shadow' THEN t.member_event_ids
                   ELSE (SELECT coalesce(jsonb_agg(DISTINCT x), '[]'::jsonb)
                         FROM jsonb_array_elements(t.member_event_ids || f.member_event_ids) x) END,
                   last_updated_at = now()
            FROM stories f WHERE t.id = :into AND f.id = :s
            """
        ),
        {"into": str(into), "s": str(story_id)},
    )
    await session.execute(
        text("UPDATE stories SET merged_into = :into, last_updated_at = now(), "
             "status = CASE WHEN status = 'shadow' THEN 'shadow' ELSE 'dormant' END WHERE id = :s"),
        {"into": str(into), "s": str(story_id)},
    )
    return moved
