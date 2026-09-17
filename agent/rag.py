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

from common.config import get_settings
from common.db import session_scope
from common.embeddings import embed_query
from common.llm import get_llm
from common.logging import get_logger
from common.models import AgentMessage, AgentSession
from common.moderation import REFUSAL, guard_question
from common.observability import fetch_prompt

logger = get_logger(__name__)

TOP_K = 8


@dataclass
class GroundingChunk:
    number: int
    article_id: uuid.UUID
    source_name: str
    url: str | None
    text: str


async def retrieve_grounding(event_id: uuid.UUID, question: str) -> tuple[list[GroundingChunk], dict, str]:
    """Top-K chunks from the event's member articles + structured projection."""
    query_vec = await embed_query(question)
    vector_literal = "[" + ",".join(f"{v:.6f}" for v in query_vec) + "]"

    async with session_scope() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT ac.article_id, ac.text, s.name AS source_name, ri.url,
                           (ac.embedding <=> CAST(:vec AS vector)) AS dist
                    FROM article_chunks ac
                    JOIN event_memberships em ON em.article_id = ac.article_id
                    JOIN articles a ON a.id = ac.article_id
                    JOIN raw_items ri ON ri.id = a.raw_item_id
                    JOIN sources s ON s.id = ri.source_id
                    WHERE em.event_id = :eid AND ac.embedding IS NOT NULL
                    ORDER BY dist ASC
                    LIMIT :k
                    """
                ),
                {"vec": vector_literal, "eid": str(event_id), "k": TOP_K},
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
) -> AsyncIterator[dict]:
    """Yield SSE-ready events: {type: token|citations|done|error, ...}."""
    # Guardrail: reject explicit/harmful/injection/spam before spending the agent.
    guard = await guard_question(question)
    if not guard.allowed:
        await _persist_turn(session_id, question, REFUSAL, [])
        yield {"type": "token", "text": REFUSAL}
        yield {"type": "citations", "citations": []}
        yield {"type": "done"}
        return

    chunks, projection, title = await retrieve_grounding(event_id, question)

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
    try:
        response = await client.chat.completions.create(
            model=settings.prism_model_agent,
            messages=messages,
            stream=True,
            # An answer is a paragraph with citations; the provider's default
            # ceiling was reserved against the balance on every question.
            max_tokens=3000,
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
                full_text += delta
                yield {"type": "token", "text": delta}
    except Exception:
        logger.exception("agent_completion_failed", event_id=str(event_id))
        yield {"type": "error", "message": "The agent is unavailable right now. Please retry."}
        return

    cited = _extract_citations(full_text, chunks)
    await _persist_turn(session_id, question, full_text, [c.article_id for c in cited])
    yield {
        "type": "citations",
        "citations": [
            {
                "number": c.number,
                "article_id": str(c.article_id),
                "source_name": c.source_name,
                "url": c.url,
            }
            for c in cited
        ],
    }
    yield {"type": "done"}


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
