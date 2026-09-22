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

from common.pair_judge import RIGHT_TEXT_CHARS, PairJudge
from common.pair_judge import judge_pairs as _judge_pairs

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


async def _fetch_posts(db: AsyncSession, ids: list[str]) -> dict[str, str]:
    rows = (await db.execute(text(
        "SELECT p.post_id, p.text, a.name, to_char(p.created_at, 'DD Mon HH24:MI') FROM x_posts p "
        "JOIN x_accounts a ON a.handle = p.handle WHERE p.post_id = ANY(CAST(:ids AS text[]))"
    ), {"ids": ids})).all()
    return {r[0]: f"POST by {r[2]} ({r[3]}):\n{r[1][:RIGHT_TEXT_CHARS]}" for r in rows}


CRITERIA = {
    "event": "the post reports, announces or comments on this very happening — the same decision, release, "
             "incident or statement the story's headline names",
    "topic": "a post from the same ministry, regulator or company about a different announcement, meeting, scheme "
             "or day; a post that shares the people, the place or the theme; a post announcing something to come "
             "when the story is what then happened, or the reverse",
    "unrelated": "a greeting, anniversary, congratulation or routine schedule, or nothing to do with the story",
}

XPOST_JUDGE = PairJudge(
    system=SYSTEM,
    criteria=CRITERIA,
    cache_table="x_post_verdicts",
    right_column="post_id",
    right_sql_type="text",
    fetch_right=_fetch_posts,
    trace_name="xpost-judge",
    log_event="xpost_judged",
)


async def judge_pairs(db: AsyncSession, pairs: list[tuple[uuid.UUID, str]]) -> dict[tuple[uuid.UUID, str], str]:
    """Verdicts for (event_id, post_id) pairs, from the cache where it has them."""
    return await _judge_pairs(db, XPOST_JUDGE, pairs)
