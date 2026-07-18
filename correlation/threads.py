"""Cross-event thread linking (war → shipping halt → oil-price coverage).

Runs inside the serial correlation consumer after an event's projection is
rebuilt, so linking never races cluster assignment. Candidates come from
cheap SQL (shared entities, then mid-band embedding distance); one batched
LLM call confirms/rejects; every verdict — including rejections — persists
to event_links so a pair is never asked twice.
"""

import uuid

from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.logging import get_logger
from common.observability import fetch_prompt
from correlation.schemas import ThreadLinkResult

logger = get_logger(__name__)

MAX_CANDIDATES = 3
WINDOW_DAYS = 14
# Below 0.12 the articles would have merged into one event (clustering
# threshold); the mid band is "related, not identical". Cross-sector links
# (war→stocks) mostly arrive via entity overlap, not embedding proximity.
EMBED_NEAR = 0.12
EMBED_FAR = 0.45


async def link_event_threads(event_id: uuid.UUID) -> None:
    candidates = await _find_candidates(event_id)
    candidates = await _drop_known_pairs(event_id, candidates)
    if not candidates:
        return

    async with session_scope() as session:
        event = (
            await session.execute(
                text("SELECT title, summary, sector, occurred_at FROM events WHERE id = :eid"),
                {"eid": str(event_id)},
            )
        ).mappings().first()
    if event is None:
        return

    candidate_lines = [
        f"[{i}] title={c['title']} | sector={c['sector']} | occurred={c['occurred_at']} | summary={(c['summary'] or '(none)')[:400]}"
        for i, c in enumerate(candidates)
    ]
    prompt = fetch_prompt("thread-link")
    messages = prompt.compile(
        title=event["title"],
        sector=event["sector"] or "unknown",
        occurred_at=str(event["occurred_at"] or "unknown"),
        summary=(event["summary"] or "(none)")[:600],
        candidates="\n".join(candidate_lines),
    )
    result = await structured_chat(
        model=get_settings().prism_model_correlate,
        messages=messages,
        output_model=ThreadLinkResult,
        trace_name="thread-link",
        metadata={"stage": "correlation", "event_id": str(event_id)},
        langfuse_prompt=prompt if prompt.version else None,
    )

    judged = {j.index: j for j in result.judgements}
    async with session_scope() as session:
        for i, candidate in enumerate(candidates):
            j = judged.get(i)
            if j is None or not j.related:
                relation, from_id, to_id = "none", event_id, candidate["id"]
                confidence, rationale = (j.confidence if j else None), (j.rationale if j else None)
            else:
                confidence, rationale = j.confidence, j.rationale
                if j.direction == "candidate_causes_event":
                    relation, from_id, to_id = "leads_to", candidate["id"], event_id
                elif j.direction == "event_causes_candidate":
                    relation, from_id, to_id = "leads_to", event_id, candidate["id"]
                else:
                    relation, from_id, to_id = "related", event_id, candidate["id"]
            await session.execute(
                text(
                    """
                    INSERT INTO event_links (id, from_event_id, to_event_id, relation, confidence, rationale)
                    VALUES (:id, :f, :t, :rel, :conf, :rat)
                    ON CONFLICT ON CONSTRAINT uq_event_links_pair DO NOTHING
                    """
                ),
                {
                    "id": str(uuid.uuid4()),
                    "f": str(from_id),
                    "t": str(to_id),
                    "rel": relation,
                    "conf": confidence,
                    "rat": rationale,
                },
            )
    linked = sum(1 for j in result.judgements if j.related)
    if linked:
        logger.info("thread_links_created", event_id=str(event_id), linked=linked)


async def _find_candidates(event_id: uuid.UUID) -> list[dict]:
    """Recent events sharing entities, then near-but-not-duplicate embeddings."""
    async with session_scope() as session:
        rows = (
            await session.execute(
                text(
                    f"""
                    (
                        SELECT e.id, e.title, e.summary, e.sector, e.occurred_at,
                               COUNT(*) AS shared, 0.0 AS dist
                        FROM event_entities mine
                        JOIN event_entities theirs
                          ON theirs.entity_id = mine.entity_id AND theirs.event_id != mine.event_id
                        JOIN events e ON e.id = theirs.event_id
                        WHERE mine.event_id = :eid
                          AND e.last_updated_at > now() - interval '{WINDOW_DAYS} days'
                        GROUP BY e.id, e.title, e.summary, e.sector, e.occurred_at
                        ORDER BY shared DESC
                        LIMIT {MAX_CANDIDATES}
                    )
                    UNION ALL
                    (
                        SELECT e.id, e.title, e.summary, e.sector, e.occurred_at,
                               0 AS shared,
                               (e.embedding <=> (SELECT embedding FROM events WHERE id = :eid)) AS dist
                        FROM events e
                        WHERE e.id != :eid
                          AND e.embedding IS NOT NULL
                          AND (SELECT embedding FROM events WHERE id = :eid) IS NOT NULL
                          AND e.last_updated_at > now() - interval '{WINDOW_DAYS} days'
                          AND (e.embedding <=> (SELECT embedding FROM events WHERE id = :eid))
                              BETWEEN {EMBED_NEAR} AND {EMBED_FAR}
                        ORDER BY dist ASC
                        LIMIT {MAX_CANDIDATES}
                    )
                    """
                ),
                {"eid": str(event_id)},
            )
        ).mappings().all()
    seen: set[uuid.UUID] = set()
    out: list[dict] = []
    for row in rows:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        out.append(dict(row))
        if len(out) >= MAX_CANDIDATES:
            break
    return out


async def _drop_known_pairs(event_id: uuid.UUID, candidates: list[dict]) -> list[dict]:
    if not candidates:
        return []
    ids = [str(c["id"]) for c in candidates]
    async with session_scope() as session:
        rows = (
            await session.execute(
                text(
                    """
                    SELECT from_event_id, to_event_id FROM event_links
                    WHERE (from_event_id = :eid AND to_event_id = ANY(CAST(:ids AS uuid[])))
                       OR (to_event_id = :eid AND from_event_id = ANY(CAST(:ids AS uuid[])))
                    """
                ),
                {"eid": str(event_id), "ids": ids},
            )
        ).all()
    known = {r[0] for r in rows} | {r[1] for r in rows}
    return [c for c in candidates if c["id"] not in known]


def format_thread_node(row) -> dict:
    return {
        "event_id": str(row["id"]),
        "title": row["title"],
        "sector": row["sector"],
        "occurred_at": row["occurred_at"].isoformat() if row["occurred_at"] else None,
        "relation": row["relation"],
        "rationale": row["rationale"],
        "confidence": row["confidence"],
        "image_url": row["image_url"],
    }


# Chain traversal: only confident causal edges make the displayed chain —
# an inaccurate chain is worse than a short one.
CHAIN_MIN_CONFIDENCE = 0.55
CHAIN_MAX_DEPTH = 3
CHAIN_MAX_NODES = 8


async def _walk_chain(session, event_id: uuid.UUID, direction: str) -> list[dict]:
    """Multi-hop walk over leads_to edges (ancestors or descendants)."""
    frontier = {str(event_id)}
    seen = {str(event_id)}
    out: list[dict] = []
    for _ in range(CHAIN_MAX_DEPTH):
        if not frontier or len(out) >= CHAIN_MAX_NODES:
            break
        near, far = ("to_event_id", "from_event_id") if direction == "up" else ("from_event_id", "to_event_id")
        rows = (
            await session.execute(
                text(
                    f"""
                    SELECT e.id, e.title, e.sector, e.occurred_at, e.image_url,
                           l.relation, l.rationale, l.confidence, l.from_event_id
                    FROM event_links l
                    JOIN events e ON e.id = l.{far}
                    WHERE l.{near} = ANY(CAST(:ids AS uuid[]))
                      AND l.relation = 'leads_to'
                      AND COALESCE(l.confidence, 1.0) >= {CHAIN_MIN_CONFIDENCE}
                    """
                ),
                {"ids": list(frontier)},
            )
        ).mappings().all()
        frontier = set()
        for row in rows:
            rid = str(row["id"])
            if rid in seen:
                continue  # cycle guard
            seen.add(rid)
            frontier.add(rid)
            out.append(format_thread_node(row))
            if len(out) >= CHAIN_MAX_NODES:
                break
    out.sort(key=lambda n: n["occurred_at"] or "")
    return out


async def fetch_thread(event_id: uuid.UUID) -> dict:
    """The event's news chain: multi-hop causal ancestors (what led here),
    multi-hop descendants (what followed), plus direct 'related' context."""
    async with session_scope() as session:
        upstream = await _walk_chain(session, event_id, "up")
        downstream = await _walk_chain(session, event_id, "down")
        related = (
            await session.execute(
                text(
                    """
                    SELECT e.id, e.title, e.sector, e.occurred_at, e.image_url,
                           l.relation, l.rationale, l.confidence, l.from_event_id
                    FROM event_links l
                    JOIN events e ON e.id = CASE WHEN l.from_event_id = :eid THEN l.to_event_id ELSE l.from_event_id END
                    WHERE (l.from_event_id = :eid OR l.to_event_id = :eid)
                      AND l.relation = 'related'
                    ORDER BY e.occurred_at NULLS LAST
                    """
                ),
                {"eid": str(event_id)},
            )
        ).mappings().all()
    # Related context rides above the chain (no causal position of its own).
    upstream = [format_thread_node(r) for r in related] + upstream
    return {"upstream": upstream, "downstream": downstream}
