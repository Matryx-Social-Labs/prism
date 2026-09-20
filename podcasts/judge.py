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
from typing import Literal

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.llm import REASONING_OFF, structured_chat
from common.logging import get_logger

logger = get_logger(__name__)


class Verdict(BaseModel):
    about: Literal["event", "topic", "unrelated"] = Field(
        description="event: the passage discusses this specific news event (the same happening, decision or announcement); "
        "topic: the same subject or people but a different happening, or a passing mention, or a show's intro/segue; "
        "unrelated: neither"
    )


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


async def judge_pairs(db: AsyncSession, pairs: list[tuple[uuid.UUID, uuid.UUID]]) -> dict[tuple[uuid.UUID, uuid.UUID], str]:
    """Verdicts for (event_id, window_id) pairs, from the cache where it has them."""
    if not pairs:
        return {}
    model = get_settings().prism_model_judge
    cached = {
        (r[0], r[1]): r[2]
        for r in (await db.execute(text(
            "SELECT event_id, window_id, verdict FROM clip_verdicts WHERE (event_id, window_id) IN "
            "(SELECT unnest(CAST(:e AS uuid[])), unnest(CAST(:w AS uuid[])))"
        ), {"e": [p[0] for p in pairs], "w": [p[1] for p in pairs]})).all()
    }
    todo = [p for p in pairs if p not in cached]
    if todo:
        events = {r[0]: r for r in (await db.execute(text(
            "SELECT id, title, projection->'lens_briefs'->>'reader' AS brief, to_char(first_seen_at, 'DD Mon HH24:MI') AS seen "
            "FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"
        ), {"ids": list({p[0] for p in todo})})).all()}
        windows = {r[0]: (r[1], r[2]) for r in (await db.execute(text(
            "SELECT w.id, w.text, to_char(e.published_at, 'DD Mon HH24:MI') FROM podcast_windows w JOIN podcast_episodes e ON e.id = w.episode_id "
            "WHERE w.id = ANY(CAST(:ids AS uuid[]))"
        ), {"ids": list({p[1] for p in todo})})).all()}
    judged = 0
    for ev_id, w_id in todo:
        ev = events.get(ev_id)
        win = windows.get(w_id)
        if not ev or not win:
            continue
        passage, aired = win
        brief = ". ".join((ev[2] or "").split(". ")[:2])
        try:
            out = await structured_chat(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"STORY headline: {ev[1]}\nSTORY first reported: {ev[3]}\nSTORY record: {brief[:600]}\n\nPASSAGE (episode aired {aired}):\n{passage[:1600]}"},
                ],
                output_model=Verdict,
                trace_name="clip-judge",
                temperature=0,  # a verdict, not a draft: the same pair must judge the same way twice
                max_tokens=40,
                reasoning=REASONING_OFF,
            )
            verdict = out.about
        except Exception as exc:  # noqa: BLE001 — an unjudged pair is simply not a clip this run
            logger.warning("clip_judge_failed", event=str(ev_id), window=str(w_id), error=str(exc)[:160])
            continue
        await db.execute(text(
            "INSERT INTO clip_verdicts (event_id, window_id, verdict, model) VALUES (:e, :w, :v, :m) "
            "ON CONFLICT (event_id, window_id) DO UPDATE SET verdict = EXCLUDED.verdict, model = EXCLUDED.model"
        ), {"e": ev_id, "w": w_id, "v": verdict, "m": model})
        cached[(ev_id, w_id)] = verdict
        judged += 1
    if judged:
        logger.info("clip_judged", pairs=judged, model=model)
    return cached


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
