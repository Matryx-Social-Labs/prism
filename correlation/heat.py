"""What is breaking: a record many outlets report fast, in more than one language.

Counted, never judged. Each outlet counts once per record, at its first article's
own publication time — windowed as the timeline is (correlation/chronology), so a
bogus RSS date falls back to when Prism attached it. A record first reported in
the last LOOKBACK_HOURS breaks when, within WINDOW_MIN of that first report,
>= prism_breaking_min_outlets outlets in >= prism_breaking_min_languages
languages have reported it — unless it was anticipated: its story (story_events)
already had >= ANTICIPATED_OUTLETS outlets on records first reported 1-72 hours
before. A medal or a match result is the latest development of its story, not
breaking news.

Calibrated 2026-10-01 on 16 days of production arrivals: >= 6 outlets / >= 2
languages fired 0-8 times a day; with the anticipated rule, ~1.6 a day (an actor's
death, a suicide bombing, a drowning, a Supreme Court order).
"""

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.logging import get_logger

logger = get_logger(__name__)

LOOKBACK_HOURS = 3
WINDOW_MIN = 120
ANTICIPATED_OUTLETS = 3

_MARK = f"""
WITH cand AS (
    SELECT e.id, coalesce(e.first_published_at, e.first_seen_at) AS t0, e.first_seen_at
    FROM events e
    WHERE e.merged_into IS NULL AND e.breaking_at IS NULL
      AND coalesce(e.first_published_at, e.first_seen_at) > now() - interval '{LOOKBACK_HOURS} hours'
),
arr AS (
    SELECT c.id, coalesce(src.publisher, src.slug) AS outlet, ri.language AS lang,
           min(CASE WHEN ri.published_at BETWEEN c.first_seen_at - interval '7 days' AND c.first_seen_at + interval '1 hour'
                    THEN ri.published_at ELSE m.created_at END) AS t
    FROM cand c
    JOIN event_memberships m ON m.event_id = c.id
    JOIN articles a ON a.id = m.article_id
    JOIN raw_items ri ON ri.id = a.raw_item_id
    JOIN sources src ON src.id = ri.source_id
    GROUP BY c.id, outlet, ri.language
),
counts AS (
    SELECT c.id, c.t0,
           count(DISTINCT arr.outlet) FILTER (WHERE arr.t <= c.t0 + interval '{WINDOW_MIN} minutes') AS outlets,
           count(DISTINCT arr.lang) FILTER (WHERE arr.t <= c.t0 + interval '{WINDOW_MIN} minutes') AS langs
    FROM cand c JOIN arr ON arr.id = c.id
    GROUP BY c.id, c.t0
)
UPDATE events e SET breaking_at = now(), breaking_outlets = k.outlets, breaking_languages = k.langs
FROM counts k
WHERE e.id = k.id AND k.outlets >= :min_outlets AND k.langs >= :min_langs
  AND NOT EXISTS (
      SELECT 1
      FROM story_events se
      JOIN story_events se2 ON se2.story_id = se.story_id AND se2.event_id <> se.event_id
      JOIN events e2 ON e2.id = se2.event_id AND e2.merged_into IS NULL
      JOIN event_memberships m2 ON m2.event_id = e2.id
      JOIN articles a2 ON a2.id = m2.article_id
      JOIN raw_items r2 ON r2.id = a2.raw_item_id
      JOIN sources s2 ON s2.id = r2.source_id
      WHERE se.event_id = k.id
        AND coalesce(e2.first_published_at, e2.first_seen_at)
            BETWEEN k.t0 - interval '72 hours' AND k.t0 - interval '1 hour'
      HAVING count(DISTINCT coalesce(s2.publisher, s2.slug)) >= {ANTICIPATED_OUTLETS}
  )
RETURNING e.id, e.title, k.outlets, k.langs
"""


async def mark_breaking(session: AsyncSession) -> int:
    """Mark the records that crossed the breaking bar since the last pass
    (prism_breaking shadow|live). Returns how many."""
    settings = get_settings()
    if settings.prism_breaking not in ("shadow", "live"):
        return 0
    rows = (await session.execute(text(_MARK), {"min_outlets": settings.prism_breaking_min_outlets,
                                                "min_langs": settings.prism_breaking_min_languages})).all()
    for r in rows:
        logger.info("breaking", event_id=str(r.id), title=(r.title or "")[:80], outlets=r.outlets, languages=r.langs,
                    mode=settings.prism_breaking)
    return len(rows)
