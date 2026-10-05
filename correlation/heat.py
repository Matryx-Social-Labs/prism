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

Counts cannot tell a sudden happening from a widely carried statement: in shadow,
4 of 11 firings were a speech, a pledge, a campaign launch and a candidate list
(2026-10-05). Each candidate is now asked once whether it reports a sudden
happening (SUDDEN); on 18 labelled candidates every happening read >= 0.83 and
five of six statements <= 0.31, so it breaks at >= SUDDEN_MIN. The reading is
kept in breaking_sudden, so no candidate is asked twice.
"""

import asyncio

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.decisions import Noul, NoulAnswer, decide
from common.logging import get_logger
from correlation.verify import VERIFY_TIMEOUT_S

logger = get_logger(__name__)

LOOKBACK_HOURS = 3
WINDOW_MIN = 120
ANTICIPATED_OUTLETS = 3
SUDDEN_MIN = 0.6
SUDDEN = (
    "{a} reports a sudden happening: something that just occurred or was just decided, such as a death, accident, "
    "attack, crime, disaster, arrest, deportation, court ruling or order, official ban or finding, resignation or "
    "retirement, or the result of a contest or award. Not a statement, speech, criticism, promise, pledge, campaign "
    "or initiative launch, list of party candidates, routine price, fare or schedule change, or a reaction to earlier news"
)

_MARK = f"""
WITH cand AS (
    SELECT e.id, coalesce(e.first_published_at, e.first_seen_at) AS t0, e.first_seen_at
    FROM events e
    WHERE e.merged_into IS NULL AND e.breaking_at IS NULL AND e.breaking_sudden IS NULL
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
SELECT k.id, e.title, e.summary, k.outlets, k.langs
FROM counts k JOIN events e ON e.id = k.id
WHERE k.outlets >= :min_outlets AND k.langs >= :min_langs
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
"""


async def mark_breaking(session: AsyncSession) -> int:
    """Mark the records that crossed the breaking bar since the last pass
    (prism_breaking shadow|live). Returns how many."""
    settings = get_settings()
    if settings.prism_breaking not in ("shadow", "live"):
        return 0
    rows = (await session.execute(text(_MARK), {"min_outlets": settings.prism_breaking_min_outlets,
                                                "min_langs": settings.prism_breaking_min_languages})).all()
    marked = 0
    for r in rows:
        try:
            sudden = await _sudden(r)
        except Exception as exc:  # noqa: BLE001 — an unread candidate is asked again on the next pass
            logger.warning("breaking_judge_failed", event_id=str(r.id), error=str(exc)[:160])
            continue
        breaks = sudden >= SUDDEN_MIN
        await session.execute(
            text("UPDATE events SET breaking_sudden = :p, breaking_outlets = :o, breaking_languages = :l, "
                 "breaking_at = CASE WHEN :b THEN now() END WHERE id = :e"),
            {"p": sudden, "o": r.outlets, "l": r.langs, "b": breaks, "e": str(r.id)},
        )
        marked += breaks
        logger.info("breaking" if breaks else "breaking_refused", event_id=str(r.id), title=(r.title or "")[:80],
                    outlets=r.outlets, languages=r.langs, sudden=round(sudden, 3), mode=settings.prism_breaking)
    return marked


async def _sudden(r) -> float:
    """The judge's p that the record reports a sudden happening. Network only."""
    d = await asyncio.wait_for(
        decide({"REPORT": f"Headline: {r.title}\nSummary: {(r.summary or '')[:400]}"},
               {"sudden": Noul(instructions=SUDDEN.format(a="REPORT"))},
               trace_name="breaking-sudden", metadata={"stage": "breaking", "event_id": str(r.id)}),
        VERIFY_TIMEOUT_S,
    )
    answer = d.answers["sudden"]
    assert isinstance(answer, NoulAnswer)
    return answer.noul
