"""Who covers what with whom: outlets linked by the stories they both reported
(admin charts, founder decision V4, 2026-09-24).

A story is an event created in the period; an outlet reported it if any of its
reports is a member. Two outlets are linked by how many stories both reported.
Per pair of languages, the stories reported in both — counted once per story,
however many outlets carried it. Few stories shared across two languages
while each language reports plenty is what the cross-language merge hole looks
like from here; it is a count, not a verdict on any one story.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.metrics import DAY_IST

# ponytail: the whole pair join runs in Postgres per request; with ~50 outlets
# that is a few thousand rows. Cache or pre-aggregate if outlets reach the hundreds.
MAX_OUTLETS = 120

REPORTED = f"""
    WITH m AS (
        SELECT DISTINCT m.event_id, ri.source_id
        FROM event_memberships m JOIN articles a ON a.id = m.article_id
        JOIN raw_items ri ON ri.id = a.raw_item_id JOIN events e ON e.id = m.event_id
        WHERE {DAY_IST.format(col='e.created_at')} BETWEEN :a AND :b),
    many AS (SELECT event_id FROM m GROUP BY event_id HAVING count(*) >= 2)
"""


async def network(db: AsyncSession, w: dict) -> dict[str, Any]:
    p = {"a": w["start"], "b": w["end"], "n": MAX_OUTLETS}
    outlets = (await db.execute(text(REPORTED + """
        SELECT s.id::text AS id, s.name, coalesce(s.language, 'unknown') AS language, s.country,
               count(*) AS stories, count(*) FILTER (WHERE m.event_id IN (SELECT event_id FROM many)) AS shared
        FROM m JOIN sources s ON s.id = m.source_id
        GROUP BY s.id ORDER BY stories DESC LIMIT :n"""), p)).mappings().all()
    links = (await db.execute(text(REPORTED + """
        SELECT x.source_id::text AS a, y.source_id::text AS b, count(*) AS shared
        FROM m x JOIN m y ON x.event_id = y.event_id AND x.source_id < y.source_id
        GROUP BY 1, 2 ORDER BY 3 DESC"""), p)).mappings().all()
    langs = """, ml AS (SELECT DISTINCT m.event_id, coalesce(s.language, 'unknown') AS lang
                         FROM m JOIN sources s ON s.id = m.source_id)"""
    pairs = (await db.execute(text(REPORTED + langs + """
        SELECT x.lang AS a, y.lang AS b, count(*) AS stories
        FROM ml x JOIN ml y ON x.event_id = y.event_id AND x.lang < y.lang
        GROUP BY 1, 2 ORDER BY 3 DESC"""), p)).mappings().all()
    per_language = (await db.execute(text(REPORTED + langs + """
        SELECT lang AS language, count(*) AS stories FROM ml GROUP BY 1 ORDER BY 2 DESC"""), p)).mappings().all()
    kept = {o["id"] for o in outlets}
    return {
        "range": {k: v.isoformat() for k, v in w.items()},
        "source": "event_memberships · raw_items · sources — stories created in the period",
        "outlets": [dict(o) for o in outlets],
        "links": [dict(x) for x in links if x["a"] in kept and x["b"] in kept],
        "languages": [dict(x) for x in pairs],
        "per_language": [dict(x) for x in per_language],
    }
