"""One judge for "is this TEXT about THIS story?" pairs.

The podcast clip judge and the X post judge are the same machine — the story
block on the left, the passage or post on the right, one word back, reasoning
off, verdicts cached per pair — and differ only in the prompt, the cache table
and how the right-hand side is fetched and captioned. They were two copies of
each other until 2026-09-22; this is the one copy. Pairs are judged
concurrently and their verdicts written in one batched round trip, where the
copies asked one pair at a time and wrote one row at a time.
"""

from __future__ import annotations

import asyncio
import uuid
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.decisions import Choice, ChoiceAnswer, decide
from common.llm import REASONING_OFF, structured_chat
from common.logging import get_logger

logger = get_logger(__name__)

JUDGE_CONCURRENCY = 4
STORY_RECORD_CHARS = 600
RIGHT_TEXT_CHARS = 1600


class Verdict(BaseModel):
    about: Literal["event", "topic", "unrelated"] = Field(
        description="event: the text discusses this specific news event (the same happening, decision or announcement); "
        "topic: the same subject or people but a different happening, or a passing mention, or a show's intro/segue; "
        "unrelated: neither"
    )


@dataclass(frozen=True)
class PairJudge:
    """What differs between the judges: the prompt, where verdicts live, and
    how the right-hand side reads. fetch_right maps ids to their captioned
    text ("PASSAGE (episode aired ...):\\n...")."""

    system: str
    # The same verdict as a Jev choice: what each of event / topic / unrelated
    # means for this judge, in the literal terms Jev reads.
    criteria: dict[str, str]
    cache_table: str
    right_column: str
    right_sql_type: str
    fetch_right: Callable[[AsyncSession, list[Any]], Awaitable[dict[Any, str]]]
    trace_name: str
    log_event: str


async def story_blocks(db: AsyncSession, event_ids: set[uuid.UUID]) -> dict[uuid.UUID, str]:
    rows = (
        await db.execute(
            text(
                "SELECT id, title, projection->'lens_briefs'->>'reader' AS brief, to_char(first_seen_at, 'DD Mon HH24:MI') AS seen "
                "FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"ids": list(event_ids)},
        )
    ).all()
    return {
        eid: f"STORY headline: {title}\nSTORY first reported: {seen}\n"
        f"STORY record: {'. '.join((brief or '').split('. ')[:2])[:STORY_RECORD_CHARS]}"
        for eid, title, brief, seen in rows
    }


async def _judge_on_llm(judge: PairJudge, model: str, left: str, right: str) -> str:
    out = await structured_chat(
        model=model,
        messages=[
            {"role": "system", "content": judge.system},
            {"role": "user", "content": f"{left}\n\n{right}"},
        ],
        output_model=Verdict,
        trace_name=judge.trace_name,
        temperature=0,  # a verdict, not a draft: the same pair must judge the same way twice
        max_tokens=40,
        reasoning=REASONING_OFF,
    )
    return out.about


async def _judge_on_jev(judge: PairJudge, left: str, right: str) -> str:
    d = await decide(
        {"story": left, "text": right},
        {"about": Choice(instructions="What the text is about, relative to the story", criteria=judge.criteria)},
        trace_name=judge.trace_name,
    )
    answer = d.answers["about"]
    assert isinstance(answer, ChoiceAnswer)
    return Verdict(about=answer.choice).about  # the choice keys are the vocabulary; validate anyway


async def judge_pairs(
    db: AsyncSession, judge: PairJudge, pairs: list[tuple[uuid.UUID, Any]]
) -> dict[tuple[uuid.UUID, Any], str]:
    """Verdicts for (event_id, right_id) pairs, from the cache where it has them."""
    if not pairs:
        return {}
    settings = get_settings()
    on_jev = settings.prism_judge_backend == "decide"
    model = settings.prism_model_decide if on_jev else settings.prism_model_judge
    # Table and column names come from the frozen PairJudge constants, never from input.
    cached = {
        (r[0], r[1]): r[2]
        for r in (
            await db.execute(
                text(
                    f"SELECT event_id, {judge.right_column}, verdict FROM {judge.cache_table} "
                    f"WHERE (event_id, {judge.right_column}) IN "
                    f"(SELECT unnest(CAST(:e AS uuid[])), unnest(CAST(:r AS {judge.right_sql_type}[])))"
                ),
                {"e": [p[0] for p in pairs], "r": [p[1] for p in pairs]},
            )
        ).all()
    }
    todo = [p for p in pairs if p not in cached]
    if not todo:
        return cached
    stories = await story_blocks(db, {p[0] for p in todo})
    rights = await judge.fetch_right(db, list({p[1] for p in todo}))
    sem = asyncio.Semaphore(JUDGE_CONCURRENCY)

    async def one(ev_id: uuid.UUID, r_id: Any) -> tuple[uuid.UUID, Any, str] | None:
        left, right = stories.get(ev_id), rights.get(r_id)
        if not left or not right:
            return None
        async with sem:
            try:
                about = await (_judge_on_jev(judge, left, right) if on_jev else _judge_on_llm(judge, model, left, right))
            except Exception as exc:  # noqa: BLE001 — an unjudged pair is simply not attached this run
                # `event` is structlog's own message key — the originals wrote
                # event=str(ev_id) here and the handler itself raised TypeError.
                logger.warning(
                    f"{judge.log_event}_failed",
                    event_id=str(ev_id),
                    right=str(r_id),
                    error=str(exc)[:160],
                )
                return None
        return ev_id, r_id, about

    verdicts = [v for v in await asyncio.gather(*(one(e, r) for e, r in todo)) if v]
    if verdicts:
        await db.execute(
            text(
                f"INSERT INTO {judge.cache_table} (event_id, {judge.right_column}, verdict, model) VALUES (:e, :r, :v, :m) "
                f"ON CONFLICT (event_id, {judge.right_column}) DO UPDATE SET verdict = EXCLUDED.verdict, model = EXCLUDED.model"
            ),
            [{"e": e, "r": r, "v": v, "m": model} for e, r, v in verdicts],
        )  # executemany — one batched round trip
        logger.info(judge.log_event, pairs=len(verdicts), model=model)
    return {**cached, **{(e, r): v for e, r, v in verdicts}}
