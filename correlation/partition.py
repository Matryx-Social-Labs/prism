"""Global storyline partitioner: events → stories (Leiden) → branch tree (coherence).

Three layers (see docs/STORYLINE-DESIGN.md):
  L2 Story boundary — Leiden community detection over the IDF-weighted, embedding-
      gated, roundup-excluded, stoplisted actor graph. Computed GLOBALLY and ONCE
      (not per-read) so every development of a story reads the same boundary →
      consistency by construction, and Leiden *guarantees* well-connected
      communities (greedy modularity left 53/105-event blobs).
  L3 Branch tree — within each story, a max-coherence arborescence rooted at the
      most-corroborated event. Spine-anchored coherence (does the child share the
      ROOT's distinctive actors + embed close to the root) prunes the dual-topic
      drift (Cauvery-water vs TVK-budget) that modularity alone cannot.

Reuses the hardened edge rules from threads.py (IDF weighting, STORY_STOP_ENTITIES,
the roundup CTE, the embedding gate) — the partitioner globalises them instead of
walking a per-seed BFS. Read-only until persist=True; run `python -m correlation.partition`
for the validation harness (no writes).
"""

from __future__ import annotations

import asyncio
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from pydantic import BaseModel
from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.logging import get_logger
from correlation.threads import (
    STORY_MIN_EDGE_WEIGHT,
    STORY_MIN_SHARED,
    STORY_MAX_EMBED_DIST,
    STORY_WINDOW_DAYS,
    _ROUNDUP_CTE,
    _STORY_STOP_LIST,
)

logger = get_logger(__name__)

# Leiden resolution: higher → more, smaller stories. Tuned against the validation
# cases (CJP must stay one story with branches; Assam must not absorb Sikkim).
LEIDEN_RESOLUTION = 1.0
# Branch-tree gate: a member must share this much root-spine IDF weight AND embed
# within STORY_MAX_EMBED_DIST of the root to hang on the main tree (else it is in
# the story_id but off-spine — a weak satellite, not a branch).
SPINE_MIN_WEIGHT = 0.05


@dataclass
class Node:
    id: str
    title: str
    sector: str | None
    regions: list[str]
    occurred_at: object
    source_count: int
    actors: dict[str, float] = field(default_factory=dict)  # entity_id -> df


# ── Graph load ──────────────────────────────────────────────────────────────
# Global analogue of threads._COMPONENT_EDGES_SQL: every actor-sharing event pair
# in the window, IDF-weighted, with the roundup exclusion AND a PAIRWISE embedding
# gate (symmetric, so — unlike the seed-relative BFS gate — the graph is identical
# regardless of entry point). This symmetry is what buys consistency.
_GRAPH_EDGES_SQL = text(
    f"""
    WITH df AS (
        SELECT ee.entity_id, count(DISTINCT ee.event_id)::float AS d
        FROM event_entities ee
        JOIN events ev ON ev.id = ee.event_id
                      AND ev.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
        GROUP BY ee.entity_id
    ),
    {_ROUNDUP_CTE}
    SELECT ee1.event_id AS a, ee2.event_id AS b, sum(1.0 / df.d) AS w
    FROM event_entities ee1
    JOIN entities ent ON ent.id = ee1.entity_id
                     AND ent.entity_type IN ('person', 'organization')
                     AND ent.name <> ALL(:stop)
    JOIN df ON df.entity_id = ee1.entity_id
    JOIN event_entities ee2 ON ee2.entity_id = ee1.entity_id AND ee2.event_id > ee1.event_id
    JOIN events ea ON ea.id = ee1.event_id
                  AND ea.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
                  AND ea.id NOT IN (SELECT id FROM roundup)
    JOIN events eb ON eb.id = ee2.event_id
                  AND eb.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
                  AND eb.id NOT IN (SELECT id FROM roundup)
    WHERE (
        ea.embedding IS NULL OR eb.embedding IS NULL
        OR (ea.embedding <=> eb.embedding) <= CAST(:max_dist AS double precision)
    )
    GROUP BY ee1.event_id, ee2.event_id
    HAVING count(DISTINCT ee1.entity_id) >= :min_shared
       AND sum(1.0 / df.d) >= :min_weight
    """
)


async def _load_nodes(session) -> dict[str, Node]:
    rows = (
        await session.execute(
            text(
                f"""
                WITH {_ROUNDUP_CTE}
                SELECT e.id, e.title, e.sector, e.regions,
                       coalesce(e.occurred_at::timestamptz, e.last_updated_at) AS occ,
                       (SELECT count(*) FROM event_memberships m WHERE m.event_id = e.id) AS srcs
                FROM events e
                WHERE e.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
                  AND e.id NOT IN (SELECT id FROM roundup)
                """
            )
        )
    ).mappings().all()
    nodes = {
        str(r["id"]): Node(
            id=str(r["id"]),
            title=r["title"],
            sector=r["sector"],
            regions=list(r["regions"] or []),
            occurred_at=r["occ"],
            source_count=int(r["srcs"]),
        )
        for r in rows
    }
    # Actor sets with df (person/org, non-stoplisted) — for spine + coherence.
    arows = (
        await session.execute(
            text(
                f"""
                WITH df AS (
                    SELECT ee.entity_id, count(DISTINCT ee.event_id)::float AS d
                    FROM event_entities ee
                    JOIN events ev ON ev.id = ee.event_id
                                  AND ev.last_updated_at > now() - interval '{STORY_WINDOW_DAYS} days'
                    GROUP BY ee.entity_id
                )
                SELECT ee.event_id, ee.entity_id, df.d
                FROM event_entities ee
                JOIN entities ent ON ent.id = ee.entity_id
                                 AND ent.entity_type IN ('person', 'organization')
                                 AND ent.name <> ALL(:stop)
                JOIN df ON df.entity_id = ee.entity_id
                """
            ),
            {"stop": _STORY_STOP_LIST},
        )
    ).all()
    for event_id, entity_id, d in arows:
        n = nodes.get(str(event_id))
        if n is not None:
            n.actors[str(entity_id)] = float(d)
    return nodes


async def _load_edges(session) -> list[tuple[str, str, float]]:
    rows = (
        await session.execute(
            _GRAPH_EDGES_SQL,
            {
                "stop": _STORY_STOP_LIST,
                "min_shared": STORY_MIN_SHARED,
                "min_weight": STORY_MIN_EDGE_WEIGHT,
                "max_dist": STORY_MAX_EMBED_DIST,
            },
        )
    ).mappings().all()
    return [(str(r["a"]), str(r["b"]), float(r["w"])) for r in rows]


# ── Leiden boundary (L2) ─────────────────────────────────────────────────────
def leiden_partition(
    nodes: dict[str, Node],
    edges: list[tuple[str, str, float]],
    resolution: float = LEIDEN_RESOLUTION,
) -> dict[str, int]:
    """Partition events into stories. Isolated nodes (no qualifying edge) each get
    their own singleton story. Returns {event_id: story_label}."""
    import igraph as ig
    import leidenalg

    idx = {eid: i for i, eid in enumerate(nodes)}
    g = ig.Graph(n=len(idx))
    g.vs["name"] = list(nodes)
    weights = []
    for a, b, w in edges:
        if a in idx and b in idx:
            g.add_edge(idx[a], idx[b])
            weights.append(w)
    part = leidenalg.find_partition(
        g,
        leidenalg.RBConfigurationVertexPartition,
        weights=weights or None,
        resolution_parameter=resolution,
        seed=42,  # deterministic
    )
    return {g.vs[v]["name"]: comm for comm, members in enumerate(part) for v in members}


# ── Branch tree (L3) ─────────────────────────────────────────────────────────
def _spine(members: list[Node]) -> dict[str, float]:
    """Distinctive actors of the story root, as {entity_id: 1/df}. Root = most-
    corroborated (source_count), then earliest, then lowest id. IDF-weighting means
    a magnet in the spine (CJP df82 → 0.012) barely counts while a specific actor
    (Delhi Police df6 → 0.167) anchors the story — so a branch is 'on-spine' by
    sharing the SPECIFIC actors, not the magnet."""
    root = _root(members)
    return {eid: 1.0 / df for eid, df in root.actors.items()}


def _root(members: list[Node]) -> Node:
    return sorted(members, key=lambda n: (-n.source_count, n.occurred_at, n.id))[0]


def _spine_weight(node: Node, spine: dict[str, float]) -> float:
    return sum(spine.get(eid, 0.0) for eid in node.actors)


async def _embed_dists(session, ids: list[str]) -> dict[tuple[str, str], float]:
    """Pairwise cosine distances among a story's members (small N)."""
    if len(ids) < 2:
        return {}
    rows = (
        await session.execute(
            text(
                """
                SELECT a.id AS a, b.id AS b, (a.embedding <=> b.embedding) AS d
                FROM events a JOIN events b ON b.id > a.id
                WHERE a.id = ANY(CAST(:ids AS uuid[])) AND b.id = ANY(CAST(:ids AS uuid[]))
                  AND a.embedding IS NOT NULL AND b.embedding IS NOT NULL
                """
            ),
            {"ids": ids},
        )
    ).all()
    out: dict[tuple[str, str], float] = {}
    for a, b, d in rows:
        out[(str(a), str(b))] = float(d)
        out[(str(b), str(a))] = float(d)
    return out


def _edge_weight_map(edges: list[tuple[str, str, float]]) -> dict[tuple[str, str], float]:
    m: dict[tuple[str, str], float] = {}
    for a, b, w in edges:
        m[(a, b)] = w
        m[(b, a)] = w
    return m


def build_branch_tree(
    members: list[Node],
    edge_w: dict[tuple[str, str], float],
    embed: dict[tuple[str, str], float],
    spine: dict[str, float],
) -> tuple[str, dict[str, str | None], set[str]]:
    """Max-coherence arborescence rooted at the most-corroborated event.

    Returns (root_id, {event_id: parent_id|None}, off_spine_ids). Each non-root
    event attaches to the prior-in-time member with which it shares the most actor
    IDF weight + embedding similarity. Events that fail the spine gate (don't share
    the root's distinctive actors or embed far from the root) are flagged off-spine:
    still in the story_id, but weak satellites, not main-line branches — this is the
    Cauvery-drift cut without an LLM."""
    root = _root(members)
    order = sorted(members, key=lambda n: (n.occurred_at, n.id))
    parent: dict[str, str | None] = {root.id: None}
    off_spine: set[str] = set()
    root_dist = lambda eid: embed.get((root.id, eid), 1.0)  # noqa: E731

    for node in order:
        if node.id == root.id:
            continue
        # Spine gate: shares the root's distinctive actors AND embeds near the root.
        on_spine = _spine_weight(node, spine) >= SPINE_MIN_WEIGHT and root_dist(node.id) <= STORY_MAX_EMBED_DIST
        if not on_spine:
            off_spine.add(node.id)
        # Attach to the best prior event (root is always an eligible parent).
        priors = [p for p in order if p.occurred_at <= node.occurred_at and p.id != node.id]
        best, best_score = root, -1.0
        for p in priors:
            score = edge_w.get((p.id, node.id), 0.0) + (1.0 - embed.get((p.id, node.id), 1.0))
            if score > best_score:
                best, best_score = p, score
        parent[node.id] = best.id
    return root.id, parent, off_spine


# ── LLM veto (L3 semantic separation) ────────────────────────────────────────
# Leiden gives a coarse boundary that OVER-MERGES entangled politics: the CJP protest
# blob absorbs NEET-protest, SIR/electoral, and parliament spats because they share
# national magnets (Modi, Congress, Parliament). No local structural signal separates
# them (spine actors of a big story are themselves high-df; embeddings of "protest +
# police" all sit close). A grounded LLM veto does: given the story's identity (lead
# event + recurring cast), it judges whether a candidate is the SAME story or merely
# shares actors/themes. Validated: grounded qwen2.5:3b separates every contaminant
# (NEET/SIR/Pawar/Banerjee) while keeping the genuine developments. Runs periodically
# off the ingest path on the coherence-shortlisted members only — a handful of cheap
# calls per big story, not O(n²).
VETO_MIN_STORY_SIZE = 4   # only vet blobs big enough to over-merge
VETO_MAX_MEMBERS = 25     # cap LLM calls per story
VETO_CONCURRENCY = 3

_VETO_SYS = (
    "You group news into ongoing stories. You are given a STORY (its lead event and "
    "recurring cast) and a CANDIDATE event. Decide whether the CANDIDATE is PART OF THE "
    "SAME STORY.\n"
    "SAME STORY (same_story = true) — be inclusive here — covers: the core event and its "
    "continuations; its DIRECT CONSEQUENCES (police action at it, metro/transit closures "
    "it caused, arrests, court cases about its participants); REACTIONS to it by leaders, "
    "parties, lawyers, or institutions; and the story SPREADING to other cities or states "
    "(the same movement or cause elsewhere).\n"
    "SEPARATE STORY (same_story = false): a DIFFERENT event that only shares people, "
    "parties, police, a location, or a broad theme — e.g. an unrelated protest about a "
    "different cause, a routine administrative or electoral matter, or a parliamentary "
    "dispute on another subject."
)


class _StoryVeto(BaseModel):
    same_story: bool
    confidence: float
    reason: str


async def _recurring_cast(session, ids: list[str], limit: int = 8) -> list[str]:
    rows = (
        await session.execute(
            text(
                """
                SELECT ent.name, count(DISTINCT ee.event_id) AS n
                FROM event_entities ee
                JOIN entities ent ON ent.id = ee.entity_id
                                 AND ent.entity_type IN ('person', 'organization')
                                 AND ent.name <> ALL(:stop)
                WHERE ee.event_id = ANY(CAST(:ids AS uuid[]))
                GROUP BY ent.name HAVING count(DISTINCT ee.event_id) >= 2
                ORDER BY n DESC LIMIT :lim
                """
            ),
            {"ids": ids, "stop": _STORY_STOP_LIST, "lim": limit},
        )
    ).all()
    return [r[0] for r in rows]


async def llm_prune_story(session, root: Node, members: list[Node], model: str) -> tuple[set[str], list[dict]]:
    """Return the subset of members that the grounded LLM confirms belong to the root's
    story (root always kept), plus per-candidate verdicts for logging. Members beyond
    VETO_MAX_MEMBERS (least source_count first) are kept unvetted to bound cost."""
    ev = {
        str(r["id"]): dict(r)
        for r in (
            await session.execute(
                text("SELECT id, title, summary FROM events WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [m.id for m in members]},
            )
        ).mappings().all()
    }
    cast = await _recurring_cast(session, [m.id for m in members])
    grounding = (
        f"STORY LEAD: {ev[root.id]['title']}\n{(ev[root.id].get('summary') or '')[:320]}\n"
        f"RECURRING CAST: {', '.join(cast) or '(none)'}"
    )
    # Vet the most-corroborated members first; keep the tail unvetted if huge.
    to_vet = sorted((m for m in members if m.id != root.id), key=lambda n: -n.source_count)[:VETO_MAX_MEMBERS]
    sem = asyncio.Semaphore(VETO_CONCURRENCY)

    async def vet(m: Node) -> tuple[Node, _StoryVeto | None]:
        c = ev.get(m.id, {})
        async with sem:
            try:
                r = await structured_chat(
                    model=model,
                    messages=[
                        {"role": "system", "content": _VETO_SYS},
                        {"role": "user", "content":
                            f"{grounding}\n\nCANDIDATE: {c.get('title')}\n{(c.get('summary') or '')[:320]}\n\n"
                            "Is CANDIDATE part of the SAME story?"},
                    ],
                    output_model=_StoryVeto,
                    trace_name="story-veto",
                    metadata={"stage": "partition", "story_root": root.id},
                    temperature=0.0,  # deterministic verdicts run-to-run
                    max_retries=1,
                )
                return m, r
            except Exception as exc:  # noqa: BLE001 — a failed veto keeps the member (fail-open)
                logger.warning("story_veto_failed", event_id=m.id, error=str(exc))
                return m, None

    keep = {root.id}
    verdicts: list[dict] = []
    for m, r in await asyncio.gather(*(vet(m) for m in to_vet)):
        same = True if r is None else r.same_story
        if same:
            keep.add(m.id)
        verdicts.append({"id": m.id, "title": (ev.get(m.id, {}) or {}).get("title"),
                         "same": same, "confidence": getattr(r, "confidence", None),
                         "reason": getattr(r, "reason", "unvetted" if r is None else None)})
    # Unvetted tail (beyond the cap) stays in the story.
    vetted = {m.id for m in to_vet}
    for m in members:
        if m.id not in vetted:
            keep.add(m.id)
    return keep, verdicts


# ── Orchestration ────────────────────────────────────────────────────────────
async def compute_partition(resolution: float = LEIDEN_RESOLUTION, llm_veto: bool = False) -> dict:
    """Load the graph, partition into stories, build each story's branch tree.
    Read-only; returns a structured result for validation or persistence."""
    async with session_scope() as session:
        nodes = await _load_nodes(session)
        edges = await _load_edges(session)
        labels = leiden_partition(nodes, edges, resolution)
        edge_w = _edge_weight_map(edges)

        by_story: dict[int, list[Node]] = defaultdict(list)
        for eid, label in labels.items():
            by_story[label].append(nodes[eid])

        # LLM veto (L3): prune over-merged blobs. A pruned member splits off as its
        # own story (a later partition pass re-clusters the pruned set if it coheres).
        veto_log: list[dict] = []
        if llm_veto:
            model = get_settings().prism_model_gate  # fast relevance-style judgment
            next_label = max(by_story) + 1 if by_story else 0
            for label in list(by_story):
                members = by_story[label]
                if len(members) < VETO_MIN_STORY_SIZE:
                    continue
                root = _root(members)
                keep, verdicts = await llm_prune_story(session, root, members, model)
                veto_log.append({"story": label, "root": root.title, "verdicts": verdicts})
                dropped = [m for m in members if m.id not in keep]
                if dropped:
                    by_story[label] = [m for m in members if m.id in keep]
                    for m in dropped:
                        by_story[next_label] = [m]
                        next_label += 1

        stories = []
        for label, members in by_story.items():
            ids = [m.id for m in members]
            embed = await _embed_dists(session, ids) if len(ids) > 1 else {}
            spine = _spine(members)
            root_id, parent, off_spine = build_branch_tree(members, edge_w, embed, spine)
            stories.append(
                {
                    "story_label": label,
                    "root_id": root_id,
                    "size": len(members),
                    "members": members,
                    "parent": parent,
                    "off_spine": off_spine,
                }
            )
    return {"nodes": nodes, "edges": edges, "stories": stories, "veto_log": veto_log if llm_veto else []}


# ── Validation harness (read-only) ───────────────────────────────────────────
async def demo() -> None:
    import asyncio  # noqa: F401 (imported for symmetry; caller drives the loop)

    res = await compute_partition()
    stories = sorted(res["stories"], key=lambda s: -s["size"])
    print(f"\n=== {len(res['nodes'])} events, {len(res['edges'])} edges, {len(stories)} stories ===")
    sizes = [s["size"] for s in stories]
    multi = [s for s in stories if s["size"] > 1]
    print(f"multi-event stories: {len(multi)} | singletons: {sizes.count(1)} | largest: {sizes[0]}")

    def label_of(title_re: str) -> int | None:
        import re
        for s in stories:
            for m in s["members"]:
                if re.search(title_re, m.title or "", re.I):
                    return s["story_label"]
        return None

    for name, rx in [("CJP", r"CJP|Jantar|Cockroach|காக்ரோஜ்"), ("Assam flood", r"Assam flood"),
                     ("Sikkim tunnel", r"Sikkim.*tunnel|NHPC tunnel"), ("Cauvery/Vijay", r"Cauvery|Vijay|TVK")]:
        lab = label_of(rx)
        print(f"\n--- {name}: story #{lab} ---")
        if lab is None:
            continue
        s = next(x for x in stories if x["story_label"] == lab)
        root = next(m for m in s["members"] if m.id == s["root_id"])
        print(f"  ROOT: [{root.source_count}src] {root.title[:64]}")
        for m in sorted(s["members"], key=lambda n: (n.occurred_at, n.id)):
            if m.id == s["root_id"]:
                continue
            par = s["parent"].get(m.id)
            depth = 0
            p = par
            while p:
                depth += 1
                p = s["parent"].get(p)
            tag = " (off-spine)" if m.id in s["off_spine"] else ""
            reg = ",".join(m.regions[:3])
            print(f"  {'  ' * depth}└─ [{reg}]{tag} {m.title[:56]}")


if __name__ == "__main__":
    import asyncio

    asyncio.run(demo())
