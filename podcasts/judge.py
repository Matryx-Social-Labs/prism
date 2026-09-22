"""Is this passage about THIS story? A model reads both and says.

Candidates come from the embedding and the cast (podcasts/match.py); those
cannot tell a story from its topic on real transcripts. The judge sees the
headline, the first lines of the record and the passage, and answers one of
three words. `event` is the only one that becomes a clip. Verdicts are cached
per (event, window) in clip_verdicts, so the hourly recompute is free for
every pair it has seen. The judge model (the one that scores groundedness),
reasoning off, ≈ 700 tokens a pair. Measured 2026-09-20 on 23 clips: 0.83
precision pairwise; a comparative form (one call per window over all its
candidate stories) was worse at 0.56 — it picked "the best on the menu" even
for a headline list — so pairwise stays, and podcasts/match.py adds the
structural rule the misses pointed at (one event per story per window).
"""
from __future__ import annotations

import uuid

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.llm import REASONING_OFF, structured_chat
from common.logging import get_logger
from common.pair_judge import RIGHT_TEXT_CHARS, PairJudge
from common.pair_judge import judge_pairs as _judge_pairs

logger = get_logger(__name__)


SYSTEM = (
    "You judge whether a stretch of a news podcast transcript is about a specific news story. "
    "Answer with one word in the JSON field `about`: event, topic or unrelated. `event` only when the "
    "passage itself discusses this very happening — not merely the same people, company or theme, and not "
    "a host's introduction, segue or list of headlines. A passage that only announces that the show will cover "
    "the subject, or moves from one story to the next, is `topic`. A different announcement, speech or finding "
    "from the same conference, court, ministry or company is `topic`, not `event`: the headline names one "
    "happening and the passage must be about that one. A story that ANNOUNCES something to come (an event to be "
    "inaugurated on Thursday, a bill set for a vote, a launch due next week) is not the story of what then happened "
    "there: a passage about the happening itself is `topic` for the preview. If in doubt, `topic`."
)


async def _fetch_windows(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    rows = (await db.execute(text(
        "SELECT w.id, w.text, to_char(e.published_at, 'DD Mon HH24:MI') FROM podcast_windows w "
        "JOIN podcast_episodes e ON e.id = w.episode_id WHERE w.id = ANY(CAST(:ids AS uuid[]))"
    ), {"ids": ids})).all()
    return {r[0]: f"PASSAGE (episode aired {r[2]}):\n{r[1][:RIGHT_TEXT_CHARS]}" for r in rows}


CRITERIA = {
    "event": "the passage itself discusses this very happening — the same decision, announcement, finding or "
             "result the story's headline names",
    "topic": "the same people, company, conference, court, ministry or theme but a different happening; a host's "
             "introduction, segue or list of headlines; a passage that only announces the show will cover the "
             "subject; a preview of something to come when the story is what then happened, or the reverse",
    "unrelated": "neither this story nor its subject",
}

CLIP_JUDGE = PairJudge(
    system=SYSTEM,
    criteria=CRITERIA,
    cache_table="clip_verdicts",
    right_column="window_id",
    right_sql_type="uuid",
    fetch_right=_fetch_windows,
    trace_name="clip-judge",
    log_event="clip_judged",
)


async def judge_pairs(db: AsyncSession, pairs: list[tuple[uuid.UUID, uuid.UUID]]) -> dict[tuple[uuid.UUID, uuid.UUID], str]:
    """Verdicts for (event_id, window_id) pairs, from the cache where it has them."""
    return await _judge_pairs(db, CLIP_JUDGE, pairs)


class Pick(BaseModel):
    about: list[int] = Field(
        default_factory=list,
        description="The numbers of the stories this passage is actually about. One, unless two of them report the "
        "very same happening. A preview of an event is not the event; a different announcement from the same "
        "conference, ministry or company is not the same story",
    )


TIEBREAK = (
    "A stretch of a news podcast transcript has been judged to be about at least one of the stories below. "
    "They are close relatives: the same conference, saga or crisis. Decide which of them the passage is really "
    "about. Prefer the story whose specific happening the passage describes over a preview of it, a neighbouring "
    "development, or a story that merely shares the venue or the people. Answer in the JSON field `about` with the "
    "story numbers; usually one."
)


async def tiebreak(db: AsyncSession, window_id: uuid.UUID, event_ids: list[uuid.UUID]) -> set[uuid.UUID]:
    """A passage approved for several DIFFERENT stories: which is it about?
    Comparative, on a short menu the pairwise judge already accepted — that
    is what makes it work where a comparative judge over every candidate did
    not (it picked "the best on the menu" even for a headline list). The
    losers' cached verdicts are rewritten to `topic` so the hourly recompute
    keeps the decision."""
    model = get_settings().prism_model_judge
    events = {r[0]: r for r in (await db.execute(text(
        "SELECT id, title, projection->'lens_briefs'->>'reader' AS brief, to_char(first_seen_at, 'DD Mon HH24:MI') AS seen "
        "FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"
    ), {"ids": event_ids})).all()}
    passage = (await db.execute(text("SELECT text FROM podcast_windows WHERE id = :id"), {"id": window_id})).scalar()
    listed = [(e, events[e]) for e in event_ids if e in events]
    if not passage or len(listed) < 2:
        return set(event_ids)
    menu = "\n".join(f"{i + 1}. {ev[1]} (first reported {ev[3]}) :: {'. '.join((ev[2] or '').split('. ')[:2])[:360]}" for i, (_, ev) in enumerate(listed))
    try:
        out = await structured_chat(
            model=model,
            messages=[{"role": "system", "content": TIEBREAK}, {"role": "user", "content": f"STORIES:\n{menu}\n\nPASSAGE:\n{passage[:1600]}"}],
            output_model=Pick,
            trace_name="clip-tiebreak",
            temperature=0,
            max_tokens=40,
            reasoning=REASONING_OFF,
        )
        chosen = {listed[i - 1][0] for i in out.about if 1 <= i <= len(listed)}
    except Exception as exc:  # noqa: BLE001 — undecided: keep the best-scoring one only, decided by the caller
        logger.warning("clip_tiebreak_failed", window=str(window_id), error=str(exc)[:160])
        return set()
    for e_id, _ in listed:
        if e_id not in chosen:
            await db.execute(text(
                "UPDATE clip_verdicts SET verdict = 'topic', model = :m WHERE event_id = :e AND window_id = :w"
            ), {"m": f"{model} tiebreak", "e": e_id, "w": window_id})
    return chosen
