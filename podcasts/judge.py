"""Is this passage about THIS story? A model reads both and says.

Candidates come from the embedding and the cast (podcasts/match.py); those
cannot tell a story from its topic on real transcripts. The judge sees the
headline, the first lines of the record and the passage, and answers one of
three words. `event` is the only one that becomes a clip. Verdicts are cached
per (event, window) in clip_verdicts, so the hourly recompute is free for
every pair it has seen. The light gate model, reasoning off: ≈ 700 tokens a
pair, ≈ $0.03 for a first backlog of 400 pairs.
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
    "a host's introduction, segue or list of headlines."
)


async def judge_pairs(db: AsyncSession, pairs: list[tuple[uuid.UUID, uuid.UUID]]) -> dict[tuple[uuid.UUID, uuid.UUID], str]:
    """Verdicts for (event_id, window_id) pairs, from the cache where it has them."""
    if not pairs:
        return {}
    model = get_settings().prism_model_gate
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
            "SELECT id, title, projection->'lens_briefs'->>'reader' AS brief FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"
        ), {"ids": list({p[0] for p in todo})})).all()}
        windows = {r[0]: r[1] for r in (await db.execute(text(
            "SELECT id, text FROM podcast_windows WHERE id = ANY(CAST(:ids AS uuid[]))"
        ), {"ids": list({p[1] for p in todo})})).all()}
    judged = 0
    for ev_id, w_id in todo:
        ev = events.get(ev_id)
        passage = windows.get(w_id)
        if not ev or not passage:
            continue
        brief = ". ".join((ev[2] or "").split(". ")[:2])
        try:
            out = await structured_chat(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"STORY headline: {ev[1]}\nSTORY record: {brief[:600]}\n\nPASSAGE:\n{passage[:1600]}"},
                ],
                output_model=Verdict,
                trace_name="clip-judge",
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
