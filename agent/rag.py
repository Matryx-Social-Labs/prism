"""Per-story grounded Q&A (docs/AGENT.md).

Retrieval space = the event's member article chunks (pgvector) plus the
structured projection. Answers cite sources inline as [n]; cited article
ids are recorded on agent_messages.cited_source_ids. If the grounding set
lacks the answer, the agent says so instead of guessing.
"""

import json
import re
import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

from sqlalchemy import text

from agent.structure import TailSplitter
from common.config import get_settings
from common.db import session_scope
from common.embeddings import embed_query
from common.llm import REASONING_OFF, get_llm, reasoning_payload
from common.logging import get_logger
from common.models import AgentMessage, AgentSession
from common.moderation import REFUSAL, guard_question
from common.observability import fetch_prompt

logger = get_logger(__name__)

TOP_K = 8
# Plus reads the whole story: every development's reports, not this event's
# alone (PLAN-LAUNCH.md §2.3) — "every quote by X across this story", "what
# changed over the week". Twice the chunks, because the set is many times wider.
TOP_K_STORY = 16


@dataclass
class GroundingChunk:
    number: int
    article_id: uuid.UUID
    source_name: str
    url: str | None
    text: str


async def retrieve_grounding(event_id: uuid.UUID, question: str, *, story_wide: bool = False) -> tuple[list[GroundingChunk], dict, str]:
    """Top-K chunks from the event's member articles + structured projection.

    `story_wide` widens the article set to every event in this event's story
    (the current partition run). An event with no story membership reads as
    itself, so a Plus reader never gets LESS than a free one."""
    query_vec = await embed_query(question)
    vector_literal = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"
    scope = (
        """em.event_id IN (
            SELECT :eid
            UNION
            SELECT es2.event_id FROM event_story es1
            JOIN event_story es2 ON es2.run_id = es1.run_id AND es2.story_label = es1.story_label
            JOIN partition_runs pr ON pr.id = es1.run_id AND pr.status = 'current'
            WHERE es1.event_id = :eid
        )"""
        if story_wide
        else "em.event_id = :eid"
    )

    async with session_scope() as session:
        rows = (
            await session.execute(
                text(
                    f"""
                    SELECT ac.article_id, ac.text, s.name AS source_name, ri.url,
                           (ac.embedding <=> CAST(:vec AS vector)) AS dist
                    FROM article_chunks ac
                    JOIN event_memberships em ON em.article_id = ac.article_id
                    JOIN articles a ON a.id = ac.article_id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    JOIN sources s ON s.id = ri.source_id
                    WHERE {scope} AND ac.embedding IS NOT NULL
                    ORDER BY dist ASC
                    LIMIT :k
                    """
                ),
                {"vec": vector_literal, "eid": str(event_id), "k": TOP_K_STORY if story_wide else TOP_K},
            )
        ).mappings().all()

        event_row = (
            await session.execute(
                text("SELECT title, projection FROM events WHERE id = :eid"),
                {"eid": str(event_id)},
            )
        ).mappings().first()

    chunks = [
        GroundingChunk(
            number=i + 1,
            article_id=row["article_id"],
            source_name=row["source_name"],
            url=row["url"],
            text=row["text"],
        )
        for i, row in enumerate(rows)
    ]
    projection = (event_row or {}).get("projection") or {}
    title = (event_row or {}).get("title") or ""
    return chunks, projection, title


async def answer_stream(
    *,
    event_id: uuid.UUID,
    session_id: uuid.UUID,
    question: str,
    plan: str = "free",
) -> AsyncIterator[dict]:
    """Yield SSE-ready events: {type: token|citations|done|error, ...}.

    `plan` picks the model: Plus gets prism_model_agent; free and anonymous get
    prism_model_agent_free, which answers the same grounded prompt at about a
    sixth of the cost (BUSINESS-MODEL.md §4). Citations and refusals are the
    same contract on both."""
    # Guardrail: reject explicit/harmful/injection/spam before spending the agent.
    guard = await guard_question(question)
    if not guard.allowed:
        await _persist_turn(session_id, question, REFUSAL, [])
        yield {"type": "token", "text": REFUSAL}
        yield {"type": "citations", "citations": []}
        yield {"type": "done"}
        return

    chunks, projection, title = await retrieve_grounding(event_id, question, story_wide=plan == "plus")

    if not chunks:
        refusal = "This story has no retrievable sources yet, so I can't answer grounded questions about it."
        await _persist_turn(session_id, question, refusal, [])
        yield {"type": "token", "text": refusal}
        yield {"type": "citations", "citations": []}
        yield {"type": "done"}
        return

    sources_block = "\n\n".join(
        f"[{c.number}] ({c.source_name}) {c.text}" for c in chunks
    )
    prompt = fetch_prompt("agent-qa")
    messages = prompt.compile(
        event_title=title,
        structured=json.dumps(projection, default=str)[:3000],
        sources=sources_block,
        question=question,
    )

    settings = get_settings()
    client = get_llm()
    full_text = ""
    # The prose streams; the JSON tail after `===` is held back and delivered
    # whole (agent/structure.py). `full_text` is the prose only.
    splitter = TailSplitter()
    try:
        model = settings.prism_model_agent if plan == "plus" else settings.prism_model_agent_free
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            # An answer is a paragraph with citations; the provider's default
            # ceiling was reserved against the balance on every question.
            max_tokens=3000,
            # Thinking shares max_tokens. glm-5.3-flash spent 2,224 of the 3,000
            # thinking on "who is involved and what did they say?" and 7 of 50
            # eval answers came back EMPTY (tools/eval_ask.py, 2026-09-20).
            # Off where allowed, minimal where mandatory.
            extra_body={"reasoning": reasoning_payload(model, REASONING_OFF)},
            name="agent-qa",
            metadata={
                "stage": "agent",
                "event_id": str(event_id),
                "langfuse_session_id": str(session_id),
            },
        )
        async for part in response:
            delta = part.choices[0].delta.content if part.choices else None
            if delta:
                for out in splitter.feed(delta):
                    full_text += out
                    yield {"type": "token", "text": out}
        rest = splitter.flush()
        if rest:
            full_text += rest
            yield {"type": "token", "text": rest}
    except Exception:
        logger.exception("agent_completion_failed", event_id=str(event_id))
        yield {"type": "error", "message": "The agent is unavailable right now. Please retry."}
        return

    structure = splitter.structure()
    # A table row's citations count as much as the prose's: the reader sees them.
    marks = full_text + "".join(r.n for r in (structure.rows if structure else []))
    cited = _extract_citations(marks, chunks)
    await _persist_turn(session_id, question, full_text, [c.article_id for c in cited])
    if structure:
        yield {"type": "structure", **structure.model_dump()}
    # One entry per ARTICLE (the source list), carrying every chunk number the
    # answer used for it, so a [3] that is the same report as [1] still opens it.
    numbers = _numbers_by_article(marks, chunks)
    yield {
        "type": "citations",
        "citations": [
            {
                "number": c.number,
                "numbers": numbers.get(c.article_id, [c.number]),
                "article_id": str(c.article_id),
                "source_name": c.source_name,
                "url": c.url,
            }
            for c in cited
        ],
    }
    yield {"type": "done"}


def _numbers_by_article(answer: str, chunks: list[GroundingChunk]) -> dict[uuid.UUID, list[int]]:
    """Every referenced chunk number, grouped under its article."""
    referenced = {int(n) for n in re.findall(r"\[(\d{1,2})\]", answer)}
    out: dict[uuid.UUID, list[int]] = {}
    for c in chunks:
        if c.number in referenced:
            out.setdefault(c.article_id, []).append(c.number)
    return out


def _extract_citations(answer: str, chunks: list[GroundingChunk]) -> list[GroundingChunk]:
    referenced = {int(n) for n in re.findall(r"\[(\d{1,2})\]", answer)}
    by_number = {c.number: c for c in chunks}
    seen_articles: set[uuid.UUID] = set()
    out: list[GroundingChunk] = []
    for n in sorted(referenced):
        chunk = by_number.get(n)
        if chunk and chunk.article_id not in seen_articles:
            seen_articles.add(chunk.article_id)
            out.append(chunk)
    return out


async def _persist_turn(
    session_id: uuid.UUID, question: str, answer: str, cited_article_ids: list[uuid.UUID]
) -> None:
    async with session_scope() as session:
        session.add(AgentMessage(session_id=session_id, role="user", content=question))
        session.add(
            AgentMessage(
                session_id=session_id,
                role="assistant",
                content=answer,
                cited_source_ids=cited_article_ids or None,
            )
        )


async def ensure_session(
    event_id: uuid.UUID,
    session_id: uuid.UUID | None,
    user_ref: str | None = None,
) -> uuid.UUID:
    """Resume this event's agent session, or open one.

    `user_ref` was hardcoded to the string 'default' for every session ever
    created, so Ask usage could not be attributed to anyone — which makes
    per-user metering impossible and is a stated prerequisite for charging for
    it. NULL now means genuinely anonymous, which is a different fact from
    'default' and can be told apart from it in the existing rows.
    """
    async with session_scope() as session:
        if session_id is not None:
            existing = await session.get(AgentSession, session_id)
            if existing is not None and existing.event_id == event_id:
                # ADOPT AN ANONYMOUS SESSION ON SIGN-IN. Resuming matched on
                # (session_id, event_id) only, with no ownership check, so a
                # reader who signed in mid-conversation kept writing into a
                # NULL-user_ref session — their questions stayed uncounted
                # against the account, which is a quota bypass that needs no
                # effort to trigger. Claimed once, and never re-assigned: a
                # session already owned by someone else is left alone rather
                # than silently transferred.
                if user_ref and existing.user_ref is None:
                    existing.user_ref = user_ref
                return session_id
        new_session = AgentSession(event_id=event_id, user_ref=user_ref)
        session.add(new_session)
        await session.flush()
        return new_session.id
