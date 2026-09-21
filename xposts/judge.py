"""Is this post about THIS story? A model reads both and says.

The mechanics are podcasts/judge.py's (cache per pair, one word back, reasoning
off); the prompt is not. A transcript passage DISCUSSES a story; an official
post IS the announcement — often the very release the outlets then report. So
"the same ministry, a different announcement" is the miss to guard against,
not "the host's segue". Verdicts cached in x_post_verdicts; only `event`
attaches. No tie-break: a post approved for two stories keeps the best score
(the podcast tie-break's own fallback).
"""
from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.llm import REASONING_OFF, structured_chat
from common.logging import get_logger
from podcasts.judge import Verdict

logger = get_logger(__name__)

SYSTEM = (
    "You judge whether a post from an official account on X is about a specific news story. "
    "Answer with one word in the JSON field `about`: event, topic or unrelated. `event` only when the post "
    "reports, announces or comments on this very happening — the same decision, release, incident or "
    "statement the headline names. A post from the same ministry, regulator or company about a DIFFERENT "
    "announcement, meeting, scheme or day is `topic`, as is a post that merely shares the people, the place "
    "or the theme. A post announcing something to come is not the story of what then happened, and a story "
    "that previews an event is not the post about the event itself: that pair is `topic`. Greetings, "
    "anniversaries, congratulations and routine schedules are `unrelated` unless the headline is about them. "
    "If in doubt, `topic`."
)


async def judge_pairs(db: AsyncSession, pairs: list[tuple[uuid.UUID, str]]) -> dict[tuple[uuid.UUID, str], str]:
    """Verdicts for (event_id, post_id) pairs, from the cache where it has them."""
    if not pairs:
        return {}
    model = get_settings().prism_model_judge
    cached = {
        (r[0], r[1]): r[2]
        for r in (await db.execute(text(
            "SELECT event_id, post_id, verdict FROM x_post_verdicts WHERE (event_id, post_id) IN "
            "(SELECT unnest(CAST(:e AS uuid[])), unnest(CAST(:p AS text[])))"
        ), {"e": [p[0] for p in pairs], "p": [p[1] for p in pairs]})).all()
    }
    todo = [p for p in pairs if p not in cached]
    if todo:
        events = {r[0]: r for r in (await db.execute(text(
            "SELECT id, title, projection->'lens_briefs'->>'reader' AS brief, to_char(first_seen_at, 'DD Mon HH24:MI') AS seen "
            "FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"
        ), {"ids": list({p[0] for p in todo})})).all()}
        posts = {r[0]: (r[1], r[2], r[3]) for r in (await db.execute(text(
            "SELECT p.post_id, p.text, a.name, to_char(p.created_at, 'DD Mon HH24:MI') FROM x_posts p JOIN x_accounts a ON a.handle = p.handle "
            "WHERE p.post_id = ANY(CAST(:ids AS text[]))"
        ), {"ids": list({p[1] for p in todo})})).all()}
    judged = 0
    for ev_id, p_id in todo:
        ev = events.get(ev_id)
        post = posts.get(p_id)
        if not ev or not post:
            continue
        body, who, posted = post
        brief = ". ".join((ev[2] or "").split(". ")[:2])
        try:
            out = await structured_chat(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM},
                    {"role": "user", "content": f"STORY headline: {ev[1]}\nSTORY first reported: {ev[3]}\nSTORY record: {brief[:600]}\n\nPOST by {who} ({posted}):\n{body[:1600]}"},
                ],
                output_model=Verdict,
                trace_name="xpost-judge",
                temperature=0,  # a verdict, not a draft
                max_tokens=40,
                reasoning=REASONING_OFF,
            )
            verdict = out.about
        except Exception as exc:  # noqa: BLE001 — an unjudged pair is simply not attached this run
            logger.warning("xpost_judge_failed", event=str(ev_id), post=p_id, error=str(exc)[:160])
            continue
        await db.execute(text(
            "INSERT INTO x_post_verdicts (event_id, post_id, verdict, model) VALUES (:e, :p, :v, :m) "
            "ON CONFLICT (event_id, post_id) DO UPDATE SET verdict = EXCLUDED.verdict, model = EXCLUDED.model"
        ), {"e": ev_id, "p": p_id, "v": verdict, "m": model})
        cached[(ev_id, p_id)] = verdict
        judged += 1
    if judged:
        logger.info("xpost_judged", pairs=judged, model=model)
    return cached
