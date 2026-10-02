"""The story merge pass: a smaller story absorbed into the bigger story it is part of.

Records join one story at birth (correlation/stories.py), and a story can still
split: a splinter founded before the main story was a candidate, or one the
judge passed alongside the main story. The pass proposes pairs from what the
judge already said, never from scratch:
  - a record passed for a story other than its own (both at the join floor);
  - a story that has grown since its founding report scored >= FOUNDER_HINT
    against another story (a story of one was judged on that report at birth);
  - with `centroid` (the one-off backlog, tools/merge_stories), a small story
    and the big story whose centroid is nearest its founding report, within
    CENTROID_DIST.
The smaller story S (never a running story) is absorbed into L (a running story,
else more records, else older) when S's founding report and its latest report
each read as part of L at L's join floor + MERGE_MARGIN. Star to L, and a pass
plans each story into at most one merge, as either side, so nothing chains
within a pass (A into B and B into C would carry A unread into C); the next
pass takes up what this one left. absorb keeps S's own member list, so a
merge can be read back.

Prototype on prod, 2026-10-02 (1,563 pairs from the judge's own verdicts): at
the plain floor + 0.10, 35 of 40 read right and the 5 doubtful merges all
scored below +0.15, where 18 of 18 read right.
"""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.logging import get_logger
from correlation.stories import (
    BIG_STORY,
    WINDOW_DAYS,
    _judge,
    _record,
    _story_block,
    absorb,
    join_floor,
)

logger = get_logger(__name__)

MERGE_MARGIN = 0.15
FOUNDER_HINT = 0.5
CENTROID_DIST = 0.12  # cosine distance, founding report to a big story's centroid (the prototype's 0.88)
MAX_PAIRS = 300  # judged per pass; the rest wait for the next

_PAIRS = """
WITH RECURSIVE canon(id, root) AS (
    SELECT id, id FROM stories WHERE merged_into IS NULL AND anchor_event_id IS NOT NULL
    UNION ALL
    SELECT s.id, c.root FROM stories s JOIN canon c ON s.merged_into = c.id
),
v AS (
    SELECT sv.event_id, c.root AS story, max(sv.noul) AS noul
    FROM story_verdicts sv JOIN canon c ON c.id = sv.story_id
    WHERE sv.created_at > now() - make_interval(hours => :hours)
    GROUP BY sv.event_id, c.root
),
twice AS (  -- a record the judge passed for a story other than the one it sits in
    SELECT se.story_id AS x, v.story AS y
    FROM story_events se JOIN v ON v.event_id = se.event_id AND v.story <> se.story_id
    JOIN stories o ON o.id = v.story
    WHERE v.noul >= CASE WHEN o.scope IS NULL THEN CAST(:floor AS float) ELSE CAST(:running_floor AS float) END
),
founder AS (  -- a story whose founding report scored near another story
    SELECT st.id AS x, v.story AS y
    FROM stories st JOIN v ON v.event_id = st.anchor_event_id AND v.story <> st.id
    WHERE st.merged_into IS NULL AND v.noul >= CAST(:hint AS float)
      AND (SELECT count(*) FROM story_events x WHERE x.story_id = st.id) >= 2
)
SELECT DISTINCT LEAST(x, y) AS a, GREATEST(x, y) AS b FROM (SELECT * FROM twice UNION ALL SELECT * FROM founder) u
"""

_CENTROID_PAIRS = f"""
WITH sizes AS (
    SELECT se.story_id, count(*) AS n FROM story_events se
    JOIN stories s ON s.id = se.story_id AND s.merged_into IS NULL AND s.anchor_event_id IS NOT NULL
    GROUP BY se.story_id
),
big AS (
    SELECT s.id FROM stories s LEFT JOIN sizes z ON z.story_id = s.id
    WHERE s.merged_into IS NULL AND s.anchor_event_id IS NOT NULL
      AND s.last_updated_at > now() - interval '{WINDOW_DAYS} days'
      AND (coalesce(z.n, 0) >= :big OR s.scope IS NOT NULL)
),
centroid AS (
    SELECT se.story_id, avg(a.gist_embedding) AS c
    FROM big JOIN story_events se ON se.story_id = big.id
    JOIN events e ON e.id = se.event_id AND e.merged_into IS NULL
    JOIN event_memberships m ON m.event_id = e.id AND m.match_type = 'new_event'
    JOIN articles a ON a.id = m.article_id AND a.gist_embedding IS NOT NULL
    GROUP BY se.story_id
),
small AS (
    SELECT s.id, a.gist_embedding AS g
    FROM stories s JOIN sizes z ON z.story_id = s.id AND z.n < :big
    JOIN event_memberships m ON m.event_id = s.anchor_event_id AND m.match_type = 'new_event'
    JOIN articles a ON a.id = m.article_id AND a.gist_embedding IS NOT NULL
    WHERE s.scope IS NULL AND s.last_updated_at > now() - make_interval(hours => :hours)
)
SELECT LEAST(small.id, nearest.story_id) AS a, GREATEST(small.id, nearest.story_id) AS b FROM small
CROSS JOIN LATERAL (SELECT story_id, c <=> small.g AS d FROM centroid WHERE story_id <> small.id
                    ORDER BY c <=> small.g LIMIT 1) nearest
WHERE nearest.d <= :centroid_dist
"""

_STORY = """
SELECT s.id, s.scope, s.anchor_event_id, s.merged_into, extract(epoch FROM coalesce(s.first_seen_at, now())) AS since,
       (SELECT count(*) FROM story_events x WHERE x.story_id = s.id) AS n,
       (SELECT e.id FROM story_events x JOIN events e ON e.id = x.event_id AND e.merged_into IS NULL
        WHERE x.story_id = s.id ORDER BY coalesce(e.first_published_at, e.first_seen_at) DESC LIMIT 1) AS latest
FROM stories s WHERE s.id = :s
"""


async def _story(session: AsyncSession, sid: uuid.UUID):
    return (await session.execute(text(_STORY), {"s": str(sid)})).one_or_none()


def _orient(a, b):
    """(the story that would be absorbed, the one it would join); None when both are running stories."""
    def weight(s):
        return (s.scope is not None, s.n, -float(s.since))
    small, large = sorted((a, b), key=weight)
    return None if small.scope is not None else (small, large)


async def _readings(session: AsyncSession, small, large) -> list[float]:
    """S's founding report and its latest, each judged as part of L."""
    out = []
    for eid in dict.fromkeys(e for e in (small.anchor_event_id, small.latest) if e is not None):
        rec = await _record(session, eid)
        if rec is None:
            continue
        (part, _), = (await _judge(rec, [await _story_block(session, large.id, rec)]))[0]
        out.append(part)
    return out


async def plan_merges(session: AsyncSession, *, hours: int = 2, centroid: bool = False,
                      max_pairs: int = MAX_PAIRS) -> list[dict]:
    """Judge the pairs raised in the last `hours`; write nothing. Each merge is
    {story, into, records, parts}, in the order to apply."""
    settings = get_settings()
    params = {"hours": hours, "floor": settings.prism_story_min, "running_floor": settings.prism_story_running_min,
              "hint": FOUNDER_HINT, "big": BIG_STORY, "centroid_dist": CENTROID_DIST}
    pairs = list((await session.execute(text(_PAIRS), params)).all())
    if centroid:
        pairs += list((await session.execute(text(_CENTROID_PAIRS), params)).all())
    merges: list[dict] = []
    planned: set[uuid.UUID] = set()  # either side of a planned merge
    for a, b in list(dict.fromkeys((r.a, r.b) for r in pairs))[:max_pairs]:
        if a in planned or b in planned:
            continue
        sa, sb = await _story(session, a), await _story(session, b)
        if sa is None or sb is None or sa.merged_into or sb.merged_into:
            continue
        oriented = _orient(sa, sb)
        if oriented is None:
            continue
        small, large = oriented
        try:
            parts = await _readings(session, small, large)
        except Exception as exc:  # noqa: BLE001 — an unread pair stays apart until the next pass
            logger.warning("story_merge_judge_failed", story=str(small.id), into=str(large.id), error=str(exc)[:160])
            continue
        if parts and min(parts) >= join_floor(large.scope) + MERGE_MARGIN:
            planned.update((small.id, large.id))
            merges.append({"story": small.id, "into": large.id, "records": small.n, "parts": parts})
    logger.info("story_merge_planned", pairs=len(pairs), merges=len(merges))
    return merges


async def apply_merges(session: AsyncSession, merges: list[dict]) -> int:
    """Absorb each planned merge, under the assignment lock, following a story
    that was itself absorbed earlier in the list to where it went. Returns the
    merges applied."""
    await session.execute(text("SELECT pg_advisory_xact_lock(hashtext('stories.assign'))"))
    went: dict[uuid.UUID, uuid.UUID] = {}
    applied = 0
    for m in merges:
        into = m["into"]
        while into in went:
            into = went[into]
        if into == m["story"]:
            continue
        live = (await session.execute(
            text("SELECT count(*) FROM stories WHERE id = ANY(CAST(:i AS uuid[])) AND merged_into IS NULL"),
            {"i": [str(m["story"]), str(into)]})).scalar_one()
        if live != 2:  # one side merged since the plan was judged
            continue
        await absorb(session, into, m["story"])
        went[m["story"]] = into
        applied += 1
        logger.info("story_merge", story=str(m["story"]), into=str(into), records=m["records"], parts=m["parts"])
    return applied
