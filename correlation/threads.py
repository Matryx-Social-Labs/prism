"""Cross-event thread linking (war → shipping halt → oil-price coverage).

Runs inside the serial correlation consumer after an event's projection is
rebuilt, so linking never races cluster assignment. Candidates come from
cheap SQL (shared entities, then mid-band embedding distance); one batched
LLM call confirms/rejects; every verdict — including rejections — persists
to event_links so a pair is never asked twice.
"""

import json
import uuid

from sqlalchemy import bindparam, text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.logging import get_logger
from common.observability import fetch_prompt
from correlation.clustering import _scale
from correlation.schemas import ThreadLinkResult

logger = get_logger(__name__)

MAX_CANDIDATES = 3
WINDOW_DAYS = 14
# Below 0.12 the articles would have merged into one event (clustering
# threshold); the mid band is "related, not identical". Cross-sector links
# (war→stocks) mostly arrive via entity overlap, not embedding proximity.
# Cosine distances are not comparable across embedding models; these move with
# the configured one (correlation.clustering._SCALE).
EMBED_NEAR = _scale()["embedding"]
EMBED_FAR = _scale()["embed_far"]


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
        max_tokens=600,
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


STORY_WINDOW_DAYS = 30


# ── Canonical story timeline ────────────────────────────────────────────────
# One consistent timeline shown on EVERY development of a story, so navigating
# between developments no longer collapses the view (a hub had 6 links, a leaf
# had 1). The story is the connected component over IDF-weighted, time-decayed
# actor edges, then split into topical sub-stories by community detection.
#
# Edge weight = sum(1/df) over shared person/org actors, x exp(-lambda*days_apart).
# IDF-weighting (NOT a df cutoff) is the crux: a shared magnet contributes almost
# nothing (Cockroach Janta Party df82 -> 0.012, Trump df41 -> 0.024) while a specific
# actor carries the edge (Delhi Metro df6 -> 0.167). We must NOT exclude high-df
# actors — a huge trending story's OWN core is high-df (CJP 82, Pradhan 76, Wangchuk
# 50), and a df cutoff deleted exactly those and fragmented the story into dozens of
# orphans. Down-weight them and let modularity separate stories by structure (a magnet
# bridges communities weakly; a story's core co-occurs densely). A >=STORY_MIN_SHARED
# count floor still drops single-actor noise.
#
#   leaf B ──idf-strong── hub A ──idf-strong── {Hormuz, tankers, Momeni, ...}   ← one story
#      │
#   (only "Trump", 1/41 → too light) ── tariff story                            ← excluded
#
# ponytail: bounded per-node BFS + a 5-min cache; the df CTE re-scans per node — fold
# into one recursive CTE / precomputed df if the read path gets hot.
STORY_MIN_SHARED = 2  # floor: >=2 shared person/org actors (excludes single-actor noise)
STORY_SIZE_CAP = 30
STORY_DEPTH_CAP = 4
STORY_CACHE_TTL = 300  # seconds — the component drifts slowly; brief staleness is fine
STORY_DECAY_LAMBDA = 0.03  # edge x exp(-lambda*days): 7d -> 0.81x, 30d -> 0.41x
# Min IDF-weighted, decayed edge weight. 0.15 keeps a specific+magnet pair (Delhi Metro
# 0.167 + CJP 0.012 = 0.18) but drops a magnets-only pair (2x Trump/Congress ~0.05) —
# validated on the live CJP (regroups), Iran (splits Iran/Lebanon), and KSU (stays
# separate) stories.
STORY_MIN_EDGE_WEIGHT = 0.15
# Topical-coherence ceiling: a member must be embedding-close to the SEED, not just
# to its BFS neighbour. Same actors aren't enough — a dual-topic bridge event (e.g.
# "CM Vijay reviews Mekedatu", legitimately water AND TN-politics) is close to the
# Cauvery seed (0.47) yet also close to Vijay's unrelated politics, so an edge-relative
# gate leaks the whole TN-politics cluster in one hop. A raised IDF bar can't help
# either — a mega-story's core actors are high-df magnets (CJP df82 → 0.012), so any
# weight that drops the Cauvery↔politics bridge also drops CJP's cross-state links.
# Seed-relative embedding distance separates them: on live data Cauvery's real members
# are ≤0.47 and its contamination ≥0.62, while CJP's cross-state developments span
# 0.0–0.64. 0.55 cleans Cauvery to its 2 water events and keeps ~28/31 CJP developments
# (it trims only a duplicate and the Wangchuk-hospital tail at 0.64). Skip the gate
# when either event lacks an embedding (fall back to actor overlap).
STORY_MAX_EMBED_DIST = _scale()["story_max"]

# Story-graph stopwords: generic responders and national bodies that appear across
# unrelated stories (a flood, a tunnel collapse, and a stampede all name the NDRF,
# the Army, Fire & Emergency Services). They are never a story's own protagonist, so
# they must not carry a story edge — two events sharing only these are NOT one story.
# IDF (1/df) is meant to suppress them, but a small corpus gives them a high 1/df
# (NDRF on 4 events → 0.25), so a flood links a tunnel collapse. This makes the rule
# explicit and immediate; it self-corrects at scale but we don't wait for scale.
# Deliberately NARROW: keep specific bodies like "Delhi Police" (they DO identify a
# story) and investigative bodies like the ED/CBI (often a case's central actor).
STORY_STOP_ENTITIES = {
    "National Disaster Response Force", "NDRF",
    "State Disaster Response Force", "SDRF",
    "National Disaster Management Authority", "NDMA",
    "Fire and Emergency Services", "Fire and Rescue Services", "Fire Department",
    "Army", "Indian Army", "Air Force", "Indian Air Force", "Navy", "Indian Navy",
    "Coast Guard", "Indian Coast Guard",
    "Border Security Force", "BSF", "Central Reserve Police Force", "CRPF",
    "Central Industrial Security Force", "CISF", "Assam Rifles", "ITBP",
    "India Meteorological Department", "Indian Meteorological Department",
    "Meteorological Department", "IMD",
    "Central Water Commission", "Directorate General of Mines Safety",
}
_STORY_STOP_LIST = sorted(STORY_STOP_ENTITIES)

# Roundup / live-blog events ("Tamil Nadu Today: …", "… LIVE:") pack many unrelated
# actors into one body, so they bridge unrelated stories through the shared-actor
# graph (a daily digest mentioning Vijay + Cauvery + an ammonia leak links all three).
# Exclude them from the story component: a structural title marker AND a high entity
# count. The count is what keeps single-topic items like "IndusInd Q1 Results Today:"
# (few entities) in the graph while dropping "Tamil Nadu Today: …" digests (10-44) —
# and it never touches genuine big stories, which carry no digest/LIVE marker.
ROUNDUP_TITLE_RE = r"(\ylive\y|\y(today|digest|round-?up|briefing|bulletin|recap|wrap|highlights)\y)\s*:"
ROUNDUP_MIN_ENTITIES = 8
_ROUNDUP_CTE = f"""roundup AS (
        SELECT ev.id
        FROM events ev JOIN event_entities ee ON ee.event_id = ev.id
        WHERE ev.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
          AND ev.title ~* '{ROUNDUP_TITLE_RE}'
        GROUP BY ev.id HAVING count(*) >= {ROUNDUP_MIN_ENTITIES}
    )"""

_STRONG_NEIGHBOURS_SQL = text(
    f"""
    WITH df AS (
        SELECT ee.entity_id, count(DISTINCT ee.event_id)::float AS d
        FROM event_entities ee
        JOIN events ev ON ev.id = ee.event_id
                      AND ev.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
        GROUP BY ee.entity_id
    ),
    {_ROUNDUP_CTE}
    SELECT e.id AS id,
           coalesce(e.occurred_at::timestamptz, e.last_updated_at) AS d
    FROM event_entities ee1
    JOIN entities ent ON ent.id = ee1.entity_id AND ent.entity_type IN ('person', 'organization')
                     AND ent.name <> ALL(:stop)
    JOIN df ON df.entity_id = ee1.entity_id
    JOIN event_entities ee2 ON ee2.entity_id = ee1.entity_id AND ee2.event_id <> ee1.event_id
    JOIN events e ON e.id = ee2.event_id
                 AND e.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
    WHERE ee1.event_id = :eid
      AND e.id NOT IN (SELECT id FROM roundup)
      AND (
          e.embedding IS NULL
          OR (SELECT embedding FROM events WHERE id = :seed) IS NULL
          OR (e.embedding <=> (SELECT embedding FROM events WHERE id = :seed)) <= CAST(:max_dist AS double precision)
      )
    GROUP BY e.id, e.occurred_at, e.last_updated_at
    HAVING count(DISTINCT ee1.entity_id) >= :min_shared
       AND sum(1.0 / df.d) * exp(
               -1.0 * CAST(:lam AS double precision) * coalesce(abs(extract(epoch FROM (
                   coalesce(e.occurred_at::timestamptz, e.last_updated_at) - CAST(:node_date AS timestamptz)
               )) / 86400.0), 0)
           ) >= CAST(:min_weight AS double precision)
    """
)


async def _node_date(session, eid: str):
    row = (
        await session.execute(
            text("SELECT coalesce(occurred_at::timestamptz, last_updated_at) AS d FROM events WHERE id = :eid"),
            {"eid": eid},
        )
    ).first()
    return row[0] if row else None


async def _story_component(session, seed: uuid.UUID) -> set[str]:
    """Bounded connected component of the seed over IDF-weighted, time-decayed edges
    (the count floor, IDF weight, and decay are all enforced in the SQL)."""
    seed_s = str(seed)
    seen: set[str] = {seed_s}
    frontier: set[str] = {seed_s}
    dates: dict[str, object] = {seed_s: await _node_date(session, seed_s)}
    depth = 0
    while frontier and len(seen) < STORY_SIZE_CAP and depth < STORY_DEPTH_CAP:
        nxt: set[str] = set()
        for eid in frontier:
            rows = (
                await session.execute(
                    _STRONG_NEIGHBOURS_SQL,
                    {
                        "eid": eid,
                        "seed": seed_s,
                        "node_date": dates.get(eid),
                        "lam": STORY_DECAY_LAMBDA,
                        "min_shared": STORY_MIN_SHARED,
                        "min_weight": STORY_MIN_EDGE_WEIGHT,
                        "max_dist": STORY_MAX_EMBED_DIST,
                        "stop": _STORY_STOP_LIST,
                    },
                )
            ).mappings().all()
            for r in rows:
                rid = str(r["id"])
                if rid in seen:
                    continue
                seen.add(rid)
                dates[rid] = r["d"]
                nxt.add(rid)
                if len(seen) >= STORY_SIZE_CAP:
                    break
        frontier = nxt
        depth += 1
    return seen


_COMPONENT_EDGES_SQL = text(
    f"""
    WITH df AS (
        SELECT ee.entity_id, count(DISTINCT ee.event_id)::float AS d
        FROM event_entities ee
        JOIN events ev ON ev.id = ee.event_id
                      AND ev.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
        GROUP BY ee.entity_id
    )
    SELECT ee1.event_id AS a, ee2.event_id AS b, sum(1.0 / df.d) AS w
    FROM event_entities ee1
    JOIN entities ent ON ent.id = ee1.entity_id AND ent.entity_type IN ('person', 'organization')
                     AND ent.name <> ALL(:stop)
    JOIN df ON df.entity_id = ee1.entity_id
    JOIN event_entities ee2 ON ee2.entity_id = ee1.entity_id AND ee2.event_id > ee1.event_id
    WHERE ee1.event_id = ANY(CAST(:ids AS uuid[]))
      AND ee2.event_id = ANY(CAST(:ids AS uuid[]))
    GROUP BY ee1.event_id, ee2.event_id
    HAVING count(DISTINCT ee1.entity_id) >= :min_shared AND sum(1.0 / df.d) >= :min_weight
    """
)


async def _component_edges(session, ids: list[str]) -> list[tuple[str, str, float]]:
    """All intra-component edges, IDF-weighted (sum 1/df over shared actors)."""
    if len(ids) < 2:
        return []
    rows = (
        await session.execute(
            _COMPONENT_EDGES_SQL,
            {"ids": ids, "min_shared": STORY_MIN_SHARED, "min_weight": STORY_MIN_EDGE_WEIGHT, "stop": _STORY_STOP_LIST},
        )
    ).mappings().all()
    return [(str(r["a"]), str(r["b"]), float(r["w"])) for r in rows]


def _seed_community(node_ids: list[str], edges: list[tuple[str, str, int]], seed: uuid.UUID) -> set[str]:
    """Split the component into topical stories by modularity, return the seed's.
    A connected component can span closely-related sub-stories (Iran war vs Lebanon
    peace) linked by a few bridge actors; community detection cuts the weak bridges so
    each development shows its own tight arc. Falls back to the whole set when there
    are no edges (single-source) or the seed lands nowhere."""
    import networkx as nx
    from networkx.algorithms.community import greedy_modularity_communities

    seed_s = str(seed)
    graph = nx.Graph()
    graph.add_nodes_from(node_ids)
    for a, b, weight in edges:
        graph.add_edge(a, b, weight=weight)
    if graph.number_of_edges() == 0:
        return {seed_s}
    for community in greedy_modularity_communities(graph, weight="weight"):
        if seed_s in community:
            return {str(n) for n in community}
    return set(node_ids)


async def _assemble_timeline(session, seed: uuid.UUID, ids: list[str]) -> dict:
    events = (
        await session.execute(
            text(
                """
                SELECT e.id, e.title, e.sector, e.occurred_at, e.last_updated_at, e.image_url,
                       COALESCE((e.projection->>'source_count')::int, 1) AS source_count
                FROM events e WHERE e.id = ANY(CAST(:ids AS uuid[]))
                """
            ),
            {"ids": ids},
        )
    ).mappings().all()
    # Causal "why" notes: confident leads_to links between two story members.
    links = (
        await session.execute(
            text(
                """
                SELECT to_event_id, rationale FROM event_links
                WHERE relation = 'leads_to' AND COALESCE(confidence, 1.0) >= 0.55
                  AND from_event_id = ANY(CAST(:ids AS uuid[]))
                  AND to_event_id = ANY(CAST(:ids AS uuid[]))
                """
            ),
            {"ids": ids},
        )
    ).mappings().all()
    why = {str(row["to_event_id"]): row["rationale"] for row in links if row["rationale"]}
    # Cast: the story's recurring protagonists (person/org in >=2 of its developments,
    # most-frequent first). No df filter — the whole point is these ARE the story's
    # central, high-frequency actors (CJP, Pradhan, Wangchuk).
    cast = (
        await session.execute(
            text(
                """
                SELECT ent.name, count(DISTINCT ee.event_id) AS n
                FROM event_entities ee
                JOIN entities ent ON ent.id = ee.entity_id AND ent.entity_type IN ('person', 'organization')
                                 AND ent.name <> ALL(:stop)
                WHERE ee.event_id = ANY(CAST(:ids AS uuid[]))
                GROUP BY ent.name HAVING count(DISTINCT ee.event_id) >= 2
                ORDER BY n DESC LIMIT 8
                """
            ),
            {"ids": ids, "stop": _STORY_STOP_LIST},
        )
    ).mappings().all()
    developments = sorted(
        (
            {
                "id": str(e["id"]),
                "title": e["title"],
                "sector": e["sector"],
                "occurred_at": (e["occurred_at"] or e["last_updated_at"]).isoformat()
                if (e["occurred_at"] or e["last_updated_at"])
                else None,
                "image_url": e["image_url"],
                "is_current": str(e["id"]) == str(seed),
                "why": why.get(str(e["id"])),
                # The route map weighs a station by how many outlets filed it.
                "source_count": e["source_count"],
            }
            for e in events
        ),
        key=lambda d: d["occurred_at"] or "",
    )
    return {"developments": developments, "cast": [c["name"] for c in cast]}


async def _current_run_id(session) -> str | None:
    return (await session.execute(text("SELECT id::text FROM partition_runs WHERE status='current'"))).scalar()


async def _partitioned_members(session, event_id: uuid.UUID) -> set[str] | None:
    """Members of this event's story in the CURRENT partition run (correlation/
    partition.py), or None if the event isn't in the current run yet (created since
    the last pass → the caller falls back to the BFS component). Two indexed lookups:
    the event's (run, label), then that label's members — the global partition already
    fixed the boundary, so this is consistent from any member and needs no re-split."""
    row = (
        await session.execute(
            text("SELECT es.run_id::text AS r, es.story_label AS l FROM event_story es "
                 "JOIN partition_runs pr ON pr.id = es.run_id AND pr.status = 'current' "
                 "WHERE es.event_id = :eid"),
            {"eid": str(event_id)},
        )
    ).first()
    if row is None:
        return None
    run_id, label = row
    rows = (
        await session.execute(
            text("SELECT event_id::text FROM event_story WHERE run_id = :r AND story_label = :l"),
            {"r": run_id, "l": label},
        )
    ).scalars().all()
    return set(rows)


async def story_timeline(event_id: uuid.UUID) -> dict:
    """The canonical, consistent timeline for the story this event belongs to:
    every development in the story, chronological, with the current event marked and
    causal 'why' notes on the edges that event_links confirms. Reads the global
    partition (consistent boundary by construction); falls back to the per-seed BFS
    component for events not yet in a partition run. Cached per (current run, event)
    so a run flip invalidates instantly (fail-open)."""
    from common.stream import get_redis

    async with session_scope() as session:
        run_id = await _current_run_id(session)
    ckey = f"story_timeline:{run_id or 'bfs'}:{event_id}"
    try:
        redis = get_redis()
        cached = await redis.get(ckey)
        if cached:
            return json.loads(cached)
    except Exception:  # noqa: BLE001 — cache is best-effort; compute on any miss/error
        redis = None

    async with session_scope() as session:
        members = await _partitioned_members(session, event_id)
        if members is not None:
            result = await _assemble_timeline(session, event_id, list(members))
        else:  # not partitioned yet — the original per-seed BFS component + split
            component = list(await _story_component(session, event_id))
            edges = await _component_edges(session, component)
            community = _seed_community(component, edges, event_id)
            result = await _assemble_timeline(session, event_id, list(community))

    if redis is not None:
        try:
            await redis.set(ckey, json.dumps(result), ex=STORY_CACHE_TTL)
        except Exception:  # noqa: BLE001
            pass
    return result


async def story_timeline_from_members(seed: uuid.UUID, member_ids: list) -> dict:
    """Assemble a timeline for a GIVEN frozen member set rather than recomputing the
    boundary — keeps a /trending/<slug> share link pinned to the identity it EARNED
    even as the global partition shifts (codex #4). Used by the trending share route."""
    ids = [str(m) for m in (member_ids or [])]
    if str(seed) not in ids:
        ids.append(str(seed))
    async with session_scope() as session:
        return await _assemble_timeline(session, seed, ids)


async def branch_tree_for_members(member_ids: list) -> dict | None:
    """The persisted L3 branch tree for a FROZEN member set, shaped for the client.

    correlation/partition.py has been writing `event_story.branch_parent_id` and
    `.off_spine` every run since the storyline partitioner shipped, and nothing has
    ever read them — `_partitioned_members` selects only `story_label` and flattens.
    This is the read side.

    Returns `{root_id, nodes: [{id, parent_id, off_spine, depth}], shape: {...}}`,
    or None when the story predates the current run (the client then renders the
    flat timeline it renders today — no regression).

    The member set is the one the slug EARNED, not the live partition, so a shared
    link keeps its identity. That means a parent can be missing from the set: those
    nodes are re-attached to the root rather than dropped, otherwise the tree would
    silently lose developments the page is already showing.
    """
    ids = [str(m) for m in (member_ids or [])]
    if not ids:
        return None
    async with session_scope() as session:
        rows = (
            await session.execute(
                text(
                    "SELECT es.event_id::text AS id, es.branch_parent_id::text AS parent, es.off_spine AS off "
                    "FROM event_story es "
                    "JOIN partition_runs pr ON pr.id = es.run_id AND pr.status = 'current' "
                    "WHERE es.event_id = ANY(:ids)"
                ).bindparams(bindparam("ids", type_=ARRAY(PG_UUID(as_uuid=True)))),
                {"ids": [uuid.UUID(i) for i in ids]},
            )
        ).mappings().all()
    if not rows:
        return None

    present = {r["id"] for r in rows}
    # Root: branch_parent_id IS NULL, or the frozen set cut the parent off.
    root_id = next((r["id"] for r in rows if r["parent"] is None), None)
    if root_id is None:
        root_id = next((r["id"] for r in rows if r["parent"] not in present), rows[0]["id"])

    parent: dict[str, str | None] = {}
    for r in rows:
        p = r["parent"]
        parent[r["id"]] = None if r["id"] == root_id or p not in present else p

    def depth_of(node: str) -> int:
        d, seen = 0, {node}
        cur = parent.get(node)
        while cur is not None and cur not in seen:  # `seen` guards a cycle we should never write
            seen.add(cur)
            d += 1
            cur = parent.get(cur)
        return d

    nodes = [
        {"id": r["id"], "parent_id": parent[r["id"]], "off_spine": bool(r["off"]), "depth": depth_of(r["id"])}
        for r in rows
    ]
    nodes.sort(key=lambda n: (n["depth"], n["id"]))

    # The shape readout is COUNTED, never summarized — no LLM, nothing to hallucinate.
    children: dict[str, int] = {}
    for n in nodes:
        if n["parent_id"]:
            children[n["parent_id"]] = children.get(n["parent_id"], 0) + 1
    shape = {
        "developments": len(nodes),
        # A branch is a fork: a node whose parent has more than one child.
        "branches": sum(1 for n in nodes if n["parent_id"] and children.get(n["parent_id"], 0) > 1),
        "satellites": sum(1 for n in nodes if n["off_spine"]),
        "max_depth": max((n["depth"] for n in nodes), default=0),
    }
    return {"root_id": root_id, "nodes": nodes, "shape": shape}
