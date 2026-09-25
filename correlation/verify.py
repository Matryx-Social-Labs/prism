"""The verified matching tier's judge: does this article report the same happening
as one of these events? One Jev call reads the article and up to five candidate
events; its answers are kept in event_match_verdicts.

WHY A JUDGE AND NOT A THRESHOLD. Measured 2026-09-25 on three labelled sets
(tools/audit_event_dups, docs/CANONICALIZATION.md): similarity finds the
duplicates but cannot be trusted to merge them. Templated local news — two
cooperative societies' annual results, two districts' Lok Adalats, "rain in
Karnataka" and "rain in Kerala" — sits at cosine 0.93–0.97 on every signal, and
no cut clears those without discarding most true duplicates. Jev reads both texts:

    same-happening AUC      hard same-language   cross-language   July gold
    gist embedding alone         0.913               0.992          0.940
    Jev on headline+summary      0.993               0.985          0.964
    Jev + brief / + body         no gain (0.990/0.993, 0.985/0.983, 0.964/0.952)

At 0.85 Jev held precision 1.00 on the hard set and 20 of 20 on a random sample
of a week of production pairs. Batched (one call, several candidates) scored the
same as pairwise (AUC 0.988 vs 0.987), so an article costs one call: about
$0.00005 and 250 ms.

WHAT IT IS ASKED AGAINST. The event's founding headline and summary, which never
change (correlation/consumer.canonical_title) — so an article is judged against
the happening the event was founded on, not against whatever it has since
absorbed. Linking pairs transitively instead chained a week of Trump–Xi coverage
into one 46-event group; judged against a fixed founder, there is no chain.

The question names the traps literally because Jev is literal: a different
figure is still the same happening (the reports gave Mushtaq Khan's age as 56,
67, 75 and 76), a reaction or a follow-up is not (it joins at the story layer).
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from common.config import get_settings
from common.decisions import Noul, NoulAnswer, decide
from common.logging import get_logger

logger = get_logger(__name__)

# Jev runs under correlation's match-or-create lock, so it gets a hard ceiling:
# decide() retries and waits out quota pauses, and none of that may hold ingest.
# A timeout is a "no" — the article founds its own event, as it does today.
VERIFY_TIMEOUT_S = 6.0

SAME_HAPPENING = (
    "{a} and {b} report the same real-world happening: the same incident, death, match or race, ruling, "
    "announcement, deal, statement or protest, even when one adds details, gives different figures, is written later "
    "or in another language. They do NOT if one is a follow-up or reaction to the other, an earlier or later stage of "
    "it (a forecast and the storm's aftermath, a semifinal and the final), a different person's statement on the same "
    "issue, or another instance of a recurring kind (another cooperative society's results, another district's Lok "
    "Adalat, another day's prices or weather)"
)


@dataclass(frozen=True)
class Candidate:
    event_id: uuid.UUID
    distance: float  # nearest member article's gist, cosine distance


def gist_text(shared: dict, raw_title: str) -> str | None:
    """What the gist embeds: the extractor's headline and one-line summary, in
    English whatever the article's language. None when the extractor wrote
    neither — a raw title alone is not a gist."""
    headline = (shared.get("headline") or "").strip()
    summary = (shared.get("headline_summary") or "").strip()
    if not summary:
        return None
    return f"{headline or raw_title}. {summary}"


def article_block(*, source: str, published_at, headline: str, summary: str) -> str:
    when = published_at.strftime("%Y-%m-%d %H:%M") if published_at else "unknown"
    return f"Published {when} by {source}.\nHeadline: {headline}\nSummary: {summary}"


async def event_blocks(session: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, str]:
    """Each candidate's FOUNDING headline and summary — what the judge reads."""
    rows = (
        await session.execute(
            text("SELECT id, title, summary, first_seen_at FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(i) for i in ids]},
        )
    ).all()
    return {
        r.id: f"First reported {r.first_seen_at:%Y-%m-%d %H:%M}.\nHeadline: {r.title}\nSummary: {r.summary or ''}"
        for r in rows
    }


async def judge(
    *, article_id: uuid.UUID, block: str, candidates: list[Candidate], blocks: dict[uuid.UUID, str]
) -> tuple[list[tuple[Candidate, float]], str]:
    """Jev's probability, per candidate, that the article reports the event's
    happening, and the model that answered. The network call only — no database:
    a Jev failure or timeout raises, and the caller treats that as no match,
    which is only safe because nothing here can leave the transaction aborted."""
    asked = [c for c in candidates if c.event_id in blocks]
    if not asked:
        return [], ""
    state = {"ARTICLE": block, **{f"EVENT_{k}": blocks[c.event_id] for k, c in enumerate(asked, 1)}}
    questions = {f"same_{k}": Noul(instructions=SAME_HAPPENING.format(a="ARTICLE", b=f"EVENT_{k}"))
                 for k in range(1, len(asked) + 1)}
    d = await asyncio.wait_for(
        decide(state, questions, trace_name="event-verify", metadata={"stage": "correlation", "article_id": str(article_id)}),
        VERIFY_TIMEOUT_S,
    )
    scored = []
    for k, c in enumerate(asked, 1):
        answer = d.answers[f"same_{k}"]
        assert isinstance(answer, NoulAnswer)
        scored.append((c, answer.noul))
    return scored, d.model or get_settings().prism_model_decide


async def record(
    session: AsyncSession, *, article_id: uuid.UUID, scored: list[tuple[Candidate, float]], model: str, mode: str
) -> None:
    """Every answer, matched or not, into event_match_verdicts — the audit trail
    and the replay cache. A failure here is a database failure and propagates."""
    if not scored:
        return
    await session.execute(
        text(
            "INSERT INTO event_match_verdicts (article_id, event_id, noul, gist_distance, model, mode) "
            "VALUES (:a, :e, :n, :d, :m, :mode) "
            "ON CONFLICT (article_id, event_id) DO UPDATE SET noul = EXCLUDED.noul, model = EXCLUDED.model, mode = EXCLUDED.mode"
        ),
        [{"a": str(article_id), "e": str(c.event_id), "n": p, "d": c.distance, "m": model, "mode": mode}
         for c, p in scored],
    )  # executemany — one round trip
