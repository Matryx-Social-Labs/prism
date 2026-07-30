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
import hashlib
import json
import uuid
from collections import defaultdict
from dataclasses import dataclass, field

from pydantic import BaseModel
from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.logging import get_logger
from common.observability import fetch_prompt
from correlation.threads import (
    _ROUNDUP_CTE,
    _STORY_STOP_LIST,
    STORY_MAX_EMBED_DIST,
    STORY_MIN_EDGE_WEIGHT,
    STORY_MIN_SHARED,
    STORY_WINDOW_DAYS,
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

    def affinity(p: Node, n: Node) -> float:
        return edge_w.get((p.id, n.id), 0.0) + (1.0 - embed.get((p.id, n.id), 1.0))

    # How attractive is each candidate as a parent to the story AT LARGE?
    #
    # Raw affinity alone builds a star, not a tree. _root picks the
    # most-corroborated event, which is by construction the one sharing actors
    # with everything and sitting at the story's semantic centre — so it outscored
    # every rival parent for almost every child and collected them all. Measured on
    # a 22-development storyline before this: the root won 19 of 21 attachments,
    # none of them by a tie-break, median margin 0.73. The page then rendered one
    # undifferentiated "21 developments" row, which is a list wearing a tree's UI.
    #
    # Dividing by that mean pull is the same correction already settled for actors
    # (IDF, not a df cutoff): a candidate plausible as the parent of EVERYTHING
    # says little about any one child, so its scores are discounted accordingly.
    # Same 22-development storyline after: fan-out 19 -> 4, depth 2 -> 5. Stories
    # that already formed a chain are unaffected — there is no hub to discount.
    others = max(len(members) - 1, 1)
    pull = {
        p.id: sum(affinity(p, n) for n in members if n.id != p.id) / others
        for p in members
    }

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
            # A candidate with no pull at all has nothing to normalise away, and
            # dividing by ~0 would make its one weak edge beat every real one.
            score = affinity(p, node) / pull[p.id] if pull[p.id] > 1e-9 else 0.0
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
# The veto system prompt is a Langfuse-managed prompt `story-veto` (local fallback
# common/prompts/fallbacks/story-veto.json) — same pattern as every other stage, so
# the eval runs the exact prompt production runs and it iterates without a redeploy.


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
    prompt = fetch_prompt("story-veto")

    async def vet(m: Node) -> tuple[Node, _StoryVeto | None]:
        c = ev.get(m.id, {})
        candidate = f"{c.get('title')}\n{(c.get('summary') or '')[:320]}"
        async with sem:
            try:
                r = await structured_chat(
                    model=model,
                    messages=prompt.compile(grounding=grounding, candidate=candidate),
                    output_model=_StoryVeto,
                    trace_name="story-veto",
                    langfuse_prompt=prompt,
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
def _group_by_story(labels: dict[str, int], nodes: dict[str, Node]) -> dict[int, list[Node]]:
    by_story: dict[int, list[Node]] = defaultdict(list)
    for eid, label in labels.items():
        by_story[label].append(nodes[eid])
    return by_story


async def _apply_veto(session, by_story: dict[int, list[Node]], model: str, *,
                      version: str | None = None, base_run_id: str | None = None) -> list[dict]:
    """Prune each over-merged story with the grounded veto; a dropped member splits off
    as its own story. When version+base_run_id are given, verdicts are cached in / reused
    from story_veto so an unchanged story skips the LLM (A2:B / C2:A)."""
    veto_log: list[dict] = []
    next_label = max(by_story) + 1 if by_story else 0
    for label in list(by_story):
        members = by_story[label]
        if len(members) < VETO_MIN_STORY_SIZE:
            continue
        root = _root(members)
        if version is not None:
            keep, verdicts = await _vet_with_reuse(session, root, members, model, version, base_run_id)
        else:
            keep, verdicts = await llm_prune_story(session, root, members, model)
        veto_log.append({"story": label, "root": root.title, "verdicts": verdicts})
        dropped = [m for m in members if m.id not in keep]
        if dropped:
            by_story[label] = [m for m in members if m.id in keep]
            for m in dropped:
                by_story[next_label] = [m]
                next_label += 1
    return veto_log


async def _finalize_stories(session, by_story: dict[int, list[Node]], edge_w) -> list[dict]:
    """Build each story's branch tree — the shared tail of compute + overlay."""
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
    return stories


async def compute_partition(resolution: float = LEIDEN_RESOLUTION, llm_veto: bool = False) -> dict:
    """Load the graph, partition into stories, build each story's branch tree.
    Read-only; returns a structured result for validation or persistence."""
    async with session_scope() as session:
        nodes = await _load_nodes(session)
        edges = await _load_edges(session)
        labels = leiden_partition(nodes, edges, resolution)
        edge_w = _edge_weight_map(edges)
        by_story = _group_by_story(labels, nodes)
        veto_log = await _apply_veto(session, by_story, get_settings().prism_model_gate) if llm_veto else []
        stories = await _finalize_stories(session, by_story, edge_w)
    return {"nodes": nodes, "edges": edges, "stories": stories, "veto_log": veto_log}


# ── Verdict signature + reuse (A2:B / C2:A) ──────────────────────────────────
# A story's veto identity is label-INDEPENDENT (sorted member ids) folded with a
# config version, so a prompt/model/resolution/window/stoplist change re-vets while
# unchanged stories reuse. codex #5/#6/#9: never keys on the ephemeral Leiden label.
def veto_config_version() -> str:
    s = get_settings()
    raw = f"gate={s.prism_model_gate}|res={LEIDEN_RESOLUTION}|win={STORY_WINDOW_DAYS}|stop={len(_STORY_STOP_LIST)}|v1"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def story_signature(members: list[Node], version: str) -> str:
    ids = "|".join(sorted(m.id for m in members))
    return hashlib.sha256(f"{ids}||{version}".encode()).hexdigest()[:32]


async def _vet_with_reuse(session, root: Node, members: list[Node], model: str,
                          version: str, base_run_id: str | None) -> tuple[set[str], list[dict]]:
    """Reuse cached verdicts for a story whose signature (membership+version) is
    unchanged; only call the LLM for candidates never judged at this signature."""
    sig = story_signature(members, version)
    cand = [m for m in members if m.id != root.id]
    rows = (
        await session.execute(
            text(
                "SELECT candidate_event_id::text AS cid, same_story FROM story_veto "
                "WHERE signature = :sig AND candidate_event_id = ANY(CAST(:ids AS uuid[]))"
            ),
            {"sig": sig, "ids": [m.id for m in cand]},
        )
    ).all()
    cached: dict[str, bool] = {cid: same for cid, same in rows}
    reused = set(cached)
    uncached = [m for m in cand if m.id not in cached]
    if uncached:  # LLM only for the never-judged tail; root included for grounding
        fresh_keep, fresh_verdicts = await llm_prune_story(session, root, [root, *uncached], model)
        by_id = {v["id"]: v for v in fresh_verdicts}
        for m in uncached:
            same = m.id in fresh_keep
            v = by_id.get(m.id, {})
            await session.execute(
                text(
                    "INSERT INTO story_veto (id, signature, candidate_event_id, same_story, "
                    "confidence, reason, base_run_id, version) VALUES (:id,:sig,:cid,:same,:conf,:reason,:brid,:ver) "
                    "ON CONFLICT (signature, candidate_event_id) DO UPDATE SET "
                    "same_story=EXCLUDED.same_story, confidence=EXCLUDED.confidence, "
                    "reason=EXCLUDED.reason, base_run_id=EXCLUDED.base_run_id"
                ),
                {"id": uuid.uuid4(), "sig": sig, "cid": m.id, "same": same,
                 "conf": v.get("confidence"), "reason": (v.get("reason") or "")[:500] or None,
                 "brid": base_run_id, "ver": version},
            )
            cached[m.id] = same
    keep = {root.id}
    verdicts: list[dict] = []
    for m in cand:
        same = cached.get(m.id, True)  # fail-open
        if same:
            keep.add(m.id)
        verdicts.append({"id": m.id, "same": same, "reused": m.id in reused})
    return keep, verdicts


# ── Persistence: immutable base/overlay runs + atomic cutover (A1:A/D1:A) ─────
# One pg advisory lock namespaces the *publish* (never held across LLM calls); a
# partial-unique index on partition_runs(status='current') is the hard invariant.
_PARTITION_LOCK_KEY = 0x50415254  # "PART"
PARTITION_RETENTION = 8           # keep this many recent runs; prune older ones


def _stats_json(**kw) -> str:
    return json.dumps(kw)


async def _write_event_story(session, run_id: uuid.UUID, stories: list[dict]) -> int:
    params = [
        {"r": run_id, "e": m.id, "l": s["story_label"],
         "p": s["parent"].get(m.id), "o": m.id in s["off_spine"]}
        for s in stories for m in s["members"]
    ]
    if params:
        await session.execute(
            text("INSERT INTO event_story (run_id, event_id, story_label, branch_parent_id, off_spine) "
                 "VALUES (:r, :e, :l, :p, :o)"),
            params,  # executemany — one batched round trip
        )
    return len(params)


async def _flip_current(session, run_id: uuid.UUID) -> None:
    # Vacate the old current BEFORE claiming the new one (partial-unique index).
    await session.execute(text("UPDATE partition_runs SET status='superseded', updated_at=now() WHERE status='current'"))
    await session.execute(text("UPDATE partition_runs SET status='current', updated_at=now() WHERE id=:id"), {"id": run_id})


async def _prune_runs(session, keep: int = PARTITION_RETENTION) -> None:
    """Keep the `keep` most-recent non-current runs; delete older ones (event_story
    CASCADEs, story_veto.base_run_id SET NULL so verdicts survive for audit).

    Never delete a run another run is still built on. partition_runs references
    ITSELF — an overlay carries the base_run_id it refined — and that self-FK is
    the one this docstring used to omit, and the code with it: it is NO ACTION,
    where the other two are CASCADE and SET NULL. So pruning an old base that a
    newer, still-retained overlay pointed at raised ForeignKeyViolationError; and
    because retention is deterministic it then raised on the SAME row every 15
    minutes for days, taking the whole partition pass down with it and leaving the
    grounded veto stuck at 'pending'.

    Retaining the base rather than orphaning the overlay is the conservative
    choice — an overlay whose base is gone cannot say what it refined, and these
    rows exist to be audited. It also self-heals: the overlay ages out first, and
    the base becomes prunable on the next pass."""
    old = (
        await session.execute(
            text(
                "SELECT id FROM partition_runs "
                "WHERE status <> 'current' "
                "  AND id NOT IN (SELECT base_run_id FROM partition_runs "
                "                 WHERE base_run_id IS NOT NULL) "
                "ORDER BY created_at DESC OFFSET :k"
            ),
            {"k": keep},
        )
    ).scalars().all()
    if old:
        await session.execute(
            text("DELETE FROM partition_runs WHERE id = ANY(CAST(:ids AS uuid[]))"),
            {"ids": [str(i) for i in old]},
        )
        logger.info("partition_runs_pruned", dropped=len(old))


async def persist_base_run(resolution: float = LEIDEN_RESOLUTION) -> str:
    """Compute a fresh Leiden L2 partition and publish it as a new immutable base run
    (veto pending). The frequent worker path — cheap, no LLM."""
    res = await compute_partition(resolution=resolution, llm_veto=False)
    async with session_scope() as session:
        await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _PARTITION_LOCK_KEY})
        run_id = uuid.uuid4()
        await session.execute(
            text("INSERT INTO partition_runs (id, status, veto_state, resolution, stats) "
                 "VALUES (:id, 'building', 'pending', :res, CAST(:stats AS jsonb))"),
            {"id": run_id, "res": resolution,
             "stats": _stats_json(events=len(res["nodes"]), edges=len(res["edges"]), stories=len(res["stories"]))},
        )
        await _write_event_story(session, run_id, res["stories"])
        await _flip_current(session, run_id)
        await _prune_runs(session)
    logger.info("partition_base_published", run_id=str(run_id), stories=len(res["stories"]))
    return str(run_id)


async def persist_veto_overlay() -> str | None:
    """Refine the current base run with the grounded veto and publish an overlay run.
    LLM calls run OUTSIDE the lock; the publish CAS-checks that the base is still
    current (else a newer base won the race — discard). The slow worker path."""
    # Master switch: gated here rather than in the worker loop so an admin trigger
    # can't spend on it either. See prism_veto_enabled for why it's off in prod.
    if not get_settings().prism_veto_enabled:
        logger.info("veto_disabled", reason="prism_veto_enabled=false")
        return None
    version = veto_config_version()
    model = get_settings().prism_model_gate
    # Phase 1 (no lock): read the current base, run the veto, finalize. Verdicts persist.
    async with session_scope() as session:
        base = (
            await session.execute(text("SELECT id::text AS id, veto_state FROM partition_runs WHERE status='current'"))
        ).mappings().first()
        if base is None or base["veto_state"] == "applied":
            return None  # nothing current, or already refined
        base_id = base["id"]
        nodes = await _load_nodes(session)
        edges = await _load_edges(session)
        edge_w = _edge_weight_map(edges)
        rows = (
            await session.execute(
                text("SELECT event_id::text AS e, story_label AS l FROM event_story WHERE run_id=:r"),
                {"r": base_id},
            )
        ).all()
        by_story: dict[int, list[Node]] = defaultdict(list)
        for e, label in rows:
            n = nodes.get(e)
            if n is not None:
                by_story[label].append(n)
        veto_log = await _apply_veto(session, by_story, model, version=version, base_run_id=base_id)
        stories = await _finalize_stories(session, by_story, edge_w)
    # Phase 2 (lock + CAS): publish only if the base is still current.
    async with session_scope() as session:
        await session.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": _PARTITION_LOCK_KEY})
        still = (await session.execute(text("SELECT id::text FROM partition_runs WHERE status='current'"))).scalar()
        if still != base_id:
            logger.info("veto_overlay_discarded_stale_base", base=base_id, current=still)
            return None
        run_id = uuid.uuid4()
        await session.execute(
            text("INSERT INTO partition_runs (id, base_run_id, status, veto_state, resolution, stats) "
                 "VALUES (:id, :base, 'building', 'applied', :res, CAST(:stats AS jsonb))"),
            {"id": run_id, "base": base_id, "res": LEIDEN_RESOLUTION,
             "stats": _stats_json(stories=len(stories), vetoed=len(veto_log))},
        )
        await _write_event_story(session, run_id, stories)
        await _flip_current(session, run_id)
        await _prune_runs(session)
    logger.info("partition_overlay_published", run_id=str(run_id), base=base_id, vetoed=len(veto_log))
    return str(run_id)


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
