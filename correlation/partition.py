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
import re
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import text

from common.config import get_settings
from common.db import session_scope
from common.llm import structured_chat
from common.logging import get_logger
from common.observability import fetch_prompt
from common.text import detect_script
from correlation.clustering import _scale
from correlation.threads import (
    _ROUNDUP_CTE,
    _STORY_STOP_LIST,
    STORY_MAX_EMBED_DIST,
    STORY_MIN_SHARED,
    STORY_WINDOW_DAYS,
)

logger = get_logger(__name__)

# CPM resolution, NOT modularity's. leiden_partition uses CPMVertexPartition
# because modularity has a resolution limit and CPM does not (Fortunato &
# Barthelemy, PNAS 2007; Traag et al. 2011). Under modularity no floor could both
# split the 80-event blob and hold a real story together — same edges, same floor:
#
#     rb  1.000  floor 0.15  ->  max 80  >25=12     (blob-and-dust)
#     cpm 0.020  floor 0.15  ->  max 34  >25= 1     (blobs broken)
#
# CPM's parameter is an absolute density threshold, so it is on the scale of the
# edge weights (IDF sums), not modularity's 1.0. Do not read 0.020 as "20x finer".
LEIDEN_RESOLUTION = 0.020

# ── v2 story edges: embedding kNN unioned with the entity edges ──────────────
#
# MEASURED 2026-09-03 against the corpus gold set (tools/l2.py carries the full
# table). v1's entity-only edge rule scores F1 0.0508 on a cross-sector sample
# because 96.5% of human-judged same-story pairs have NO EDGE to merge along: a
# same-story pair shares a median of ONE actor across the corpus, and the rule
# demands two. Inside the CJP topic cluster the median is four, which is why the
# old slice reported 0.4541 and hid this completely.
#
#                       corpus F1   corpus Cdet   CJP F1   max group
#   v1 (entity only)       0.0508        0.9739   0.4541          23
#   v2 (union)             0.5930        0.5628   0.3793          17
#     CV fold A            0.0385 -> 0.6744        fold B  0.0606 -> 0.5116
#
# THE ALGORITHM DID NOT CHANGE, only what it is given. Agglomerative RAC — the
# plan's proposal — was tried across average and complete linkage, union and
# mutual kNN, k in 3..10, and blobbed every time: max group 316 to 5,214 of 5,413
# events. The embedding space is a dense continuum and linkage chains through it.
# CPM is resolution-limit free, and its resolution is exactly what pins max group
# at 17, inside Story Forest's bound of 25.
#
# The resolution moves 0.020 -> 0.20 WITH the edge set and cannot be changed
# apart from it: ten times the edges at a tenth of the density needs a different
# scale. veto_config_version folds the resolution in, so verdicts re-vet.
STORY_EMBED_KNN = 4              # mutual: k=3 loses recall, k=5 collapses to one blob
STORY_EMBED_EDGE_MAX_DIST = _scale()["story_edge_max"]  # moves with the model
STORY_ENTITY_EDGE_WEIGHT = 2.0   # entity edges as SECONDARY evidence, not a gate
LEIDEN_RESOLUTION_V2 = 0.05
# The Leiden graph's own edge floor, deliberately SEPARATE from
# threads.STORY_MIN_EDGE_WEIGHT (0.15), which the BFS timeline still uses.
#
# This floor CAME DOWN from 0.50, which is the whole point of the content gate.
# Shared-actor weight says WHO, never WHAT HAPPENED, so it was being asked to
# carry precision on its own and could not: raising it cut a story's aftermath
# (different people) while two unrelated bills sailed through on shared
# politicians. With CONTENT_MIN_SIM confirming each edge, the actor bar only has
# to propose, so it can be permissive again and stop destroying recall.
#
# Chosen from the CENTRE of a broad plateau, not the argmin — see
# tools/sweep_partition. Selecting the single best of ~150 cells on a 45-story
# gold set finds a sharp optimum whether or not one exists, and a first attempt at
# exactly that (CPM alone, tuned) LOST to production on held-out folds in both
# directions. Every config in res 0.02-0.03 x floor 0.15-0.30 x csim 0.20-0.25
# beats the old configuration on the full set; this cell is one of only two that also
# beats it on both folds independently, which is why it and not the argmin.
#
#   config                          P        R      F1     Cdet   fp   max  >25
#   rb  1.0   floor 0.50 gate     0.2709  0.5340  0.3595  0.6496  148   32   1
#   cpm 0.020 floor 0.30 csim .20 0.4344  0.5146  0.4711  0.5710   69   23   0
#
# Wrong merges more than halved (148 -> 69) for two extra wrong splits, and the
# size distribution lands on the published reference (Story Forest, CIKM 2017:
# mean 4.07, median 3, max 25) at mean 3.32, max 23, zero groups over 25.
PARTITION_MIN_EDGE_WEIGHT = 0.30

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


def _window(col: str) -> str:
    """The story window, as SQL, in ONE place.

    `:as_of` NULL means "now", which is what production passes, so this is a
    no-op there. A measurement passes a date to reconstruct the window as it
    stood then — the only way to score a gold set older than STORY_WINDOW_DAYS,
    because `last_updated_at` slides and labelled events drop out of the live
    window about a month after they are labelled. Found when the 45-story gold
    set matched 2 of 86 events against the live partition and read as a total
    failure rather than an empty join.

    The upper bound is guarded on NULL rather than always applied: against
    `now()` it is a tautology, and a tautology in a hot query is a future puzzle.
    """
    as_of = "CAST(:as_of AS timestamptz)"
    return (
        f"{col} > coalesce({as_of}, now()) - interval '{STORY_WINDOW_DAYS} days'"
        f" AND ({as_of} IS NULL OR {col} <= {as_of})"
    )


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
                      AND {_window('ev.last_updated_at')}
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
                  AND {_window('ea.last_updated_at')}
                  AND ea.id NOT IN (SELECT id FROM roundup)
    JOIN events eb ON eb.id = ee2.event_id
                  AND {_window('eb.last_updated_at')}
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


async def _load_nodes(session, as_of: datetime | None = None) -> dict[str, Node]:
    rows = (
        await session.execute(
            text(
                f"""
                WITH {_ROUNDUP_CTE}
                SELECT e.id, e.title, e.sector, e.regions,
                       coalesce(e.occurred_at::timestamptz, e.last_updated_at) AS occ,
                       (SELECT count(*) FROM event_memberships m WHERE m.event_id = e.id) AS srcs
                FROM events e
                WHERE {_window('e.last_updated_at')}
                  AND e.id NOT IN (SELECT id FROM roundup)
                """
            ),
            {"as_of": as_of},
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
                                  AND {_window('ev.last_updated_at')}
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
            {"stop": _STORY_STOP_LIST, "as_of": as_of},
        )
    ).all()
    for event_id, entity_id, d in arows:
        n = nodes.get(str(event_id))
        if n is not None:
            n.actors[str(entity_id)] = float(d)
    return nodes


async def _load_embedding_edges(
    session, as_of: datetime | None = None
) -> list[tuple[str, str, float]]:
    """Each windowed event's k nearest neighbours by cosine, kept when close enough.

    Computed in numpy rather than as a pgvector lateral join. The HNSW index is on
    `article_chunks.embedding`, not `events.embedding`, so a lateral kNN would seq
    scan the window once per row; and this is the code path that was actually
    measured offline, which matters more than elegance for a number we intend to
    quote.

    Chunked because the full similarity matrix is O(n^2): 5,413 events would be
    117MB as float32, and the window only grows.
    """
    import numpy as np

    rows = (
        await session.execute(
            text(
                f"""
                -- CAST IS LOAD-BEARING. pgvector hands `embedding` back as its
                -- TEXT form ('[0.031,-0.044,...]'), so numpy sees a list of one
                -- string per row and raises. Casting to float4[] returns real
                -- floats. Caught by test_persist_base_run_invariant_and_read.
                SELECT id::text AS id, embedding::float4[] AS embedding
                FROM events
                WHERE {_window('last_updated_at')}
                  AND embedding IS NOT NULL
                ORDER BY id
                """
            ),
            {"as_of": as_of},
        )
    ).mappings().all()
    if len(rows) < 2:
        return []

    ids = [r["id"] for r in rows]
    emb = np.asarray([r["embedding"] for r in rows], dtype="float32")
    emb /= np.linalg.norm(emb, axis=1, keepdims=True) + 1e-12

    # MUTUAL kNN, and no distance cutoff. Both halves of that matter.
    #
    # An absolute cosine cutoff is not comparable across embedding models, and it
    # was the last thing in this file still pinned to mpnet's scale. Worse, it
    # could not exploit a better representation: mE5 separates same-story from
    # different-story pairs at AUC 0.990 against mpnet's 0.955, yet scored no
    # better under a thresholded graph, because the grid was built around mpnet's
    # distances. A rank rule has no units, so no model swap can silently
    # invalidate it.
    #
    # MUTUAL rather than one-sided: requiring each to be in the other's top-k is
    # far sparser, and sparsity is what stops one bridge fusing a whole arc. The
    # measured difference is large. Snapshot of 5,413 events, gold_stories,
    # Leiden CPM on the resulting graph:
    #
    #                                   P       R      F1     Cdet   max grp
    #     mpnet, threshold (v1)      0.4519  0.4563  0.4541  0.6144    23
    #     mE5 + passage:, mutual-kNN 0.9153  0.4696  0.6207  0.5357    15
    #     mE5 + query:,   mutual-kNN 0.9545  0.5478  0.6961  0.4553    12
    #     ...unioned with entity     0.9559  0.5652  0.7104  0.4379    23  <- live
    #
    # Cross-validated on disjoint halves of the gold stories, which is the check
    # that killed a CPM configuration once before:
    #
    #                    fold A            fold B
    #     mpnet        F1 0.5556         F1 0.3250
    #     mE5+query    F1 0.7619         F1 0.6327
    #
    # Better on BOTH folds, in the same direction — what step 4 could not show.
    # k=4 is the plateau: k=3 loses recall, k=5 collapses (max group 3,511 as
    # connected components, because mutual-kNN stops being sparse).
    # AND A DISTANCE FLOOR, model-scaled. Rank alone is not enough, and removing
    # the cutoff entirely was wrong: kNN is scale-free but it ASSUMES DENSITY.
    #
    # The offline snapshot holds 5,413 events, where an event's fourth-nearest
    # neighbour is genuinely close. The live window holds 282, where it is merely
    # the fourth LEAST UNRELATED — so the rule happily linked Uber layoffs to
    # Nepal missing persons because nothing nearer existed. Measured on the live
    # window before this floor went back:
    #
    #     261 edges, distance median 0.1262, p75 0.1389, max 0.1915
    #     72% beyond the calibrated story cutoff (0.115)
    #     19% beyond mE5's DIFFERENT-event median (0.145)
    #
    # A fifth of the graph joined pairs further apart than a typical unrelated
    # pair. So: rank decides HOW MANY neighbours (scale-free, density-aware) and
    # the floor decides whether they are actually close (needs units, and now gets
    # them from _SCALE rather than a literal, so a model swap cannot silently
    # invalidate it).
    min_sim = 1.0 - STORY_EMBED_EDGE_MAX_DIST
    k = min(STORY_EMBED_KNN, len(ids) - 1)
    topk: list[set[int]] = [set() for _ in ids]
    sims_of: dict[tuple[int, int], float] = {}
    for start in range(0, len(ids), 512):
        block = emb[start:start + 512]
        sims = block @ emb.T
        for row, i in enumerate(range(start, start + len(block))):
            sims[row, i] = -1.0                     # never a neighbour of itself
            nbrs = np.argpartition(-sims[row], k)[:k]
            for j in nbrs:
                sim = float(sims[row, j])
                if sim < min_sim:
                    continue                        # too far to be anyone's story
                topk[i].add(int(j))
                sims_of[(i, int(j))] = sim
    out: dict[tuple[str, str], float] = {}
    for i, nbrs in enumerate(topk):
        for j in nbrs:
            if i >= j or i not in topk[j]:
                continue                            # one-sided: not an edge
            a, b = (ids[i], ids[j]) if ids[i] < ids[j] else (ids[j], ids[i])
            out[(a, b)] = sims_of.get((i, j), sims_of.get((j, i), 0.0))
    return [(a, b, w) for (a, b), w in out.items()]


async def _load_edges(session, as_of: datetime | None = None) -> list[tuple[str, str, float]]:
    rows = (
        await session.execute(
            _GRAPH_EDGES_SQL,
            {
                "stop": _STORY_STOP_LIST,
                "min_shared": STORY_MIN_SHARED,
                "min_weight": PARTITION_MIN_EDGE_WEIGHT,
                "max_dist": STORY_MAX_EMBED_DIST,
                "as_of": as_of,
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
    their own singleton story. Returns {event_id: story_label}.

    Nodes and edges are SORTED before the graph is built, and that is load-bearing.
    seed=42 fixes Leiden's RNG but not the vertex ordering, and Leiden's local
    moves are order-sensitive — so feeding the same graph in a different order
    reaches a different local optimum. Both inputs arrive straight from SQL, which
    guarantees no row order at all, so the story boundary was quietly varying
    between runs on identical data: 32 of 3,655 gold pairs landed in different
    groups offline vs in production, from the same 19,337 events.

    That is not just a reproducibility annoyance. Unstable boundaries mean trending
    stories churn between passes for no reason a reader could perceive, and it made
    the offline harness disagree with production about how good a config was.
    """
    import igraph as ig
    import leidenalg

    names = sorted(nodes)
    idx = {eid: i for i, eid in enumerate(names)}
    g = ig.Graph(n=len(idx))
    g.vs["name"] = names
    weights = []
    for a, b, w in sorted(edges):
        if a in idx and b in idx:
            g.add_edge(idx[a], idx[b])
            weights.append(w)
    part = leidenalg.find_partition(
        g,
        leidenalg.CPMVertexPartition,
        weights=weights or None,
        resolution_parameter=resolution,
        seed=42,
    )
    return {g.vs[v]["name"]: comm for comm, members in enumerate(part) for v in members}


# ── Content gate (L2.5) ──────────────────────────────────────────────────────
# Leiden groups events by SHARED ACTORS, and shared actors are a TOPIC signal, not
# a story signal. Nallapati et al. (Event Threading within News Topics, CIKM 2004)
# measured this directly: adding person-name overlap to news clustering made it
# WORSE, 0.50 -> 0.45 cluster F1, because "many on-topic stories share the same
# locations or persons irrespective of the event they belong to".
#
# That is why no value of PARTITION_MIN_EDGE_WEIGHT works. Raising it raises the
# ENTITY requirement, which is exactly what a story's aftermath fails (the hospital
# coverage names different people than the protest), while two unrelated bills keep
# passing it on their shared politicians. Fortunato & Barthelemy (PNAS 2007) proved
# the other half: modularity cannot resolve communities below a size that scales
# with the whole graph, so one resolution cannot both split the blob and hold a
# real story together. Tuning was never going to fix either.
#
# So: after Leiden, require CONTENT support for staying together. Two events keep
# their link only if their headlines share a non-stopword word — Story Forest's
# fine gate (Liu et al., CIKM 2017) at its published n=1.
#
# HONEST EFFECT SIZE. A first measurement claimed this cut wrong merges 43%. That
# was WRONG and the error is worth naming, because it is easy to repeat: the gate
# was applied to a `labels` dict pre-filtered to the 49 gold events, so union-find
# ran over tiny sub-slices and never saw the chains that hold a real blob together.
# Restricting the INPUT to the evaluation set inflates any splitting rule.
#
# Swept properly over the full 18,621-event partition, one snapshot, floor x gate:
#
#    floor gate  edges  max  >25  mean |      P      R     F1   Cdet   fp   fn
#     0.15  off   1347   72   12  6.17 | 0.2324 0.9041 0.3697 1.1206  218    7
#     0.15   ON   1347   72   10  6.93 | 0.2324 0.9041 0.3697 1.1206  218    7
#     0.20   ON   1065   62    8  6.17 | 0.2557 0.7671 0.3836 0.9990  163   17
#     0.30   ON    699   44    4  4.70 | 0.2460 0.4247 0.3116 1.0219   95   42
#     0.50  off    402   29    1  3.18 | 0.4833 0.3973 0.4361 0.7485   31   44
#     0.50   ON    402   29    1  3.20 | 0.5179 0.3973 0.4496 0.7296   27   44  <- live
#     0.80   ON    159   10    0  2.60 | 0.6667 0.0822 0.1463 0.9319    3   67
#
# Read it as: the FLOOR does the work (Cdet 1.12 -> 0.75), and the gate is a small
# free refinement on top of it (fp 31 -> 27, Cdet 0.7485 -> 0.7296, recall
# untouched). At floors <= 0.30 the gate changes NOTHING on the labelled slice —
# the blobs are chained together through overlapping headlines, so transitivity
# defeats it. It is worth keeping because it is monotone and costs no recall, not
# because it is the fix.
#
# THE REAL OPEN PROBLEM IS RECALL: 0.3973, with 44 wrong splits and 6 of 25 gold
# stories broken across groups. Nothing in the sweep buys precision and recall at
# once, which is the resolution limit showing through. That needs CPM (which is
# resolution-limit free) or per-topic best-parent attachment, not another floor.
CONTENT_MIN_SIM = 0.20      # headline content-word overlap an edge must clear
CONTENT_MIN_SHARED_WORDS = 1  # kept for _content_linked's callers/tests

# Function words only. Deliberately NOT a news-vocabulary stoplist ("police",
# "court", "protest"): those ARE the story signal this gate reads. An early version
# stripped every word appearing in any entity name and the link rate collapsed to
# 2%, because that deletes "police" and "court" along with the names.
_TITLE_STOP = frozenset("""
about after against amid also been before being both came come could does done
down during each else even ever every from gets give goes gone half have here
himself into itself just keep kept know last like made make many more most much
must near next none only ones other over said same says seen shall since some
such take taken than that their them then there these they this those thus told
took under until upon very want well went were what when where which while whom
whose will with within without would your
""".split())


# A word starts with a letter and may continue through Indic combining marks.
# `\w` alone is wrong for Indian scripts: matras (U+093E etc.) are nonspacing
# marks, not alphanumeric, so `[^\W\d_]{4,}` chops "पैलेट" into sub-4-char pieces
# and returns NOTHING for a Devanagari headline. That failure is silent — a title
# with no tokens shares no words with anything, so the gate would shatter every
# Hindi and Kannada story into singletons while looking like a clean split.
_WORD_RE = re.compile(r"[^\W\d_][\wऀ-ൿ]{3,}", re.UNICODE)


def _content_words(title: str) -> frozenset[str]:
    """Content words of a headline, in any script the feed carries.

    ponytail: no stemming, so "protesters"/"protestors" and singular/plural read as
    different words. Measured anyway (see the table above) — the gate is transitive,
    so a story survives on a chain of overlapping headlines and does not need every
    pair to match. Add a stemmer only if recall starts moving.
    """
    return frozenset(
        w for w in _WORD_RE.findall((title or "").lower()) if w not in _TITLE_STOP
    )


def _content_linked(a: Node, b: Node, min_shared: int = CONTENT_MIN_SHARED_WORDS) -> bool:
    """Whether two events keep their within-community link.

    Absence of evidence never splits. A headline we cannot tokenise, and a pair
    written in DIFFERENT scripts, both return True: the gold set behind the table
    above covers Latin headlines only, so applying the gate to a Hindi/Kannada pair
    would be acting on a rule that was never measured for them. Worse, the honest
    failure is silent — an untokenisable title shares zero words with everything,
    so the gate would shatter every non-Latin story into singletons and look like
    a clean split. The gate may only ever REMOVE a link it can actually justify.
    """
    if detect_script(a.title) != detect_script(b.title):
        return True
    wa, wb = _content_words(a.title), _content_words(b.title)
    if not wa or not wb:
        return True
    return len(wa & wb) >= min_shared


def content_similarity(a: Node, b: Node) -> float | None:
    """Overlap coefficient of two headlines' content words, or None for "no evidence".

    None is NOT zero. A pair written in different scripts, or a title we cannot
    tokenise, is a pair this gate knows nothing about — and the gold set behind the
    threshold is Latin-headline heavy. Scoring those as dissimilar would delete
    every cross-script edge and look like a clean result while quietly destroying
    the Hindi and Kannada stories.
    """
    if detect_script(a.title) != detect_script(b.title):
        return None
    wa, wb = _content_words(a.title), _content_words(b.title)
    if not wa or not wb:
        return None
    return len(wa & wb) / min(len(wa), len(wb))


def filter_edges_on_content(
    edges: list[tuple[str, str, float]],
    nodes: dict[str, Node],
    min_sim: float = CONTENT_MIN_SIM,
) -> list[tuple[str, str, float]]:
    """Drop actor-derived edges that no shared content supports.

    Two gates, and they are independent by design (Story Forest's coarse+fine):
    shared actors PROPOSE the link, shared content CONFIRMS it. That is why the
    actor floor can now come DOWN to 0.30 — the entity bar no longer has to carry
    precision on its own, which is what it was never able to do.
    """
    kept = []
    for a, b, w in edges:
        na, nb = nodes.get(a), nodes.get(b)
        if na is None or nb is None:
            kept.append((a, b, w))
            continue
        sim = content_similarity(na, nb)
        if sim is None or sim >= min_sim:  # no evidence never cuts
            kept.append((a, b, w))
    return kept


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

    for idx, node in enumerate(order):
        if node.id == root.id:
            continue
        # Spine gate: shares the root's distinctive actors AND embeds near the root.
        on_spine = _spine_weight(node, spine) >= SPINE_MIN_WEIGHT and root_dist(node.id) <= STORY_MAX_EMBED_DIST
        if not on_spine:
            off_spine.add(node.id)
        # Attach to the best STRICTLY EARLIER member (root is always an eligible
        # parent, via `best`'s initial value below).
        #
        # The prefix of `order`, not a filter on occurred_at. `occurred_at <= ...`
        # is not an ordering: two events sharing a timestamp were each eligible as
        # the OTHER's parent, and since affinity is symmetric they routinely chose
        # each other. Production, measured 2026-09-04: 314 mutual pairs, every one
        # of them between events with identical occurred_at, leaving 1,059 of
        # 5,559 members (19%) unable to walk up to a root at all. Not a corner —
        # 73.5% of events carry date-granularity timestamps (exact midnight),
        # because that is all their source published.
        #
        # `order` is sorted by (occurred_at, id), which IS a total order, so a
        # parent taken from the prefix is always strictly earlier and a cycle is
        # impossible by construction rather than merely unlikely. Filtering on
        # `<` instead would have been the smaller edit and the wrong one: it
        # orphans every same-day pair onto the root and flattens the tree.
        priors = order[:idx]
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


def merge_edges(
    entity_edges: list[tuple[str, str, float]],
    emb_edges: list[tuple[str, str, float]],
) -> list[tuple[str, str, float]]:
    """UNION, not intersection, and the direction matters.

    v1 made the entity rule a GATE, so a pair with one shared actor could never
    be a story however similar its coverage — which is 96.5% of real pairs. Here
    the embedding proposes and the entity edges add weight where they agree.

    Extracted from compute_partition so an offline scorer builds the same graph
    production does. A scorer that re-implements the merge drifts from the thing
    it scores, and then reports on an algorithm nobody runs.
    """
    merged: dict[tuple[str, str], float] = {}
    for a, b, w in emb_edges:
        merged[(a, b)] = w
    for a, b, w in entity_edges:
        key = (a, b) if a < b else (b, a)
        merged[key] = merged.get(key, 0.0) + STORY_ENTITY_EDGE_WEIGHT * w
    return [(a, b, w) for (a, b), w in merged.items()]


async def compute_partition(resolution: float = LEIDEN_RESOLUTION_V2, llm_veto: bool = False) -> dict:
    """Load the graph, partition into stories, build each story's branch tree.
    Read-only; returns a structured result for validation or persistence."""
    async with session_scope() as session:
        nodes = await _load_nodes(session)
        entity_edges = await _load_edges(session)
        emb_edges = await _load_embedding_edges(session)

        edges = merge_edges(entity_edges, emb_edges)

        # NO CONTENT GATE. It was measured as a small free refinement on the
        # ENTITY edges (fp 31 -> 27) and is not part of what was measured here:
        # the v2 numbers come from raw entity edges unioned with embedding kNN.
        # Applying it now would drop embedding edges for sharing no headline word,
        # which is the cross-lingual and paraphrase case the embedding exists to
        # catch. Re-measure before adding it back.
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
    raw = (
        f"gate={s.prism_model_gate}|res={LEIDEN_RESOLUTION_V2}|win={STORY_WINDOW_DAYS}"
        # The content gate changes which events are in a story, so tuning it must
        # re-vet. story_signature already covers a membership change for stories
        # that exist; this covers the config itself so a revert to the old value
        # cannot silently reuse verdicts taken under the new one.
        f"|stop={len(_STORY_STOP_LIST)}|csim={CONTENT_MIN_SIM}|floor={PARTITION_MIN_EDGE_WEIGHT}|v2"
    )
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


async def persist_base_run(resolution: float = LEIDEN_RESOLUTION_V2) -> str | None:
    """Compute a fresh Leiden L2 partition and publish it as a new immutable base run
    (veto pending). The frequent worker path — cheap, no LLM.

    Returns None when the partition came out EMPTY and was refused.

    AN EMPTY PARTITION MUST NOT SUPERSEDE A GOOD ONE. Found in production on
    2026-09-03: `event_story` held 0 rows across 9 runs and none had ever held any.
    The corpus is frozen at 2026-08-04 and STORY_WINDOW_DAYS is 30, so every event
    had just aged out of the window; each run selected nothing, produced nothing,
    wrote nothing — and then promoted itself to `current` anyway and logged
    "partition_base_published" at INFO.

    Nothing errored. `branch_tree_for_members` simply returned None for every
    story, and BranchTree fell back to the flat timeline exactly as it is designed
    to when a storyline predates the current run. The product degraded silently and
    the logs said success, which is this repo's signature failure mode.

    Refusing to promote is the fix, not widening the window: a stale corpus is a
    real condition and the honest response is to keep serving the last partition
    that meant something while saying loudly that a new one could not be built.
    """
    res = await compute_partition(resolution=resolution, llm_veto=False)
    if not res["stories"]:
        logger.error(
            "partition_empty_refusing_to_publish",
            events=len(res["nodes"]), edges=len(res["edges"]),
            window_days=STORY_WINDOW_DAYS,
            hint="no event is newer than the story window; the previous run stays current",
        )
        return None
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
