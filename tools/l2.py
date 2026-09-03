"""L2 story layer: rebuild the boundary on embeddings, and prove it beats v1.

    uv run python -m tools.l2 --baseline     # reproduce v1 on this corpus
    uv run python -m tools.l2 --sweep        # embedding + time-decay agglomerative
    uv run python -m tools.l2 --cv           # cross-validated, both fold directions

WHY A REBUILD AND NOT MORE TUNING. v1 asks one signal — IDF-weighted shared actors
— to decide what is the same story. Two published results say that cannot work.
Nallapati et al. (CIKM 2004) measured that adding person-name overlap makes news
clustering WORSE (0.50 -> 0.45 F1): entities are a topic signal, not a story
signal. Fortunato & Barthelemy (PNAS 2007) proved modularity cannot resolve
communities below a size that scales with the whole graph, so no single edge floor
can both split a 70-event blob and hold a small story together. About 200 swept
configurations later, v1 plateaus at F1 0.47. The ceiling is the representation.

THE BASELINE IS RE-MEASURED HERE, NOT QUOTED. v1's published numbers
(P 0.4344 / R 0.5146 / F1 0.4711) were taken on a 30-day window over the unfolded
entity graph. This corpus is neither: the window is gone (it had slid past 38 of
86 gold events) and 106 entity splits have since been folded. Comparing a new
algorithm against a number from a different corpus would be measuring the corpus.
So `--baseline` reproduces v1's pipeline exactly — same edge rule, same floors,
same CPM resolution, same content gate — on the same snapshot the new one sees.

WHAT IS DELIBERATELY NOT REPEATED FROM v1'S MISTAKES:

  * Time decay is a FEATURE, never a cutoff. Measured as a hard gate it looked
    weak (1.78x lift at a 1-day cutoff while discarding 66% of true pairs) and was
    dismissed on that basis. That was the wrong experiment: 1.78 is a respectable
    likelihood ratio and a terrible threshold. It enters as sim * exp(-dt/tau),
    which cannot delete a pair, only rank it lower.
  * Every configuration is cross-validated in BOTH fold directions before it is
    believed. A CPM config once beat production on the full gold set and lost on
    held-out folds both ways (train Cdet 0.18 -> held-out 1.07).
  * Structure is reported beside the pairwise score. A pairwise win with a max
    group of 89 is not a win; Story Forest (CIKM 2017) puts real stories at mean
    4.07 / median 3 / max 25 over 261 human-rated stories.

RESULT, 2026-08-29 — THE GATE IS NOT MET, AND THE REASON IS THE GOLD SET.

    v1 reproduced here                   P 0.4519  R 0.4563  F1 0.4541  Cdet 0.6144
    embedding-only agglomerative                            F1 <=0.33   blobs of 638-1164
    + kNN as a connectivity constraint                      F1 0.09     one blob of 5,334
    hybrid, mpnet                                           F1 0.4457
    hybrid, mE5, + mutual-kNN union      P 0.5570  R 0.4272  F1 0.4835  Cdet 0.6162

The last line beats v1 on F1 by 6.5% with clean structure (max 25, nothing above),
and it does not ship, because cross-validation says the number is not real:

                          fold A      fold B
    v1 baseline           0.6571      0.4848
    mE5 + kNN             0.7778      0.3404

It wins one fold and loses the other by more. That is the exact shape that already
killed one CPM configuration here. Note the baseline's own folds differ by 0.17 —
the two halves are not equally hard, and with 45 stories / 103 positive pairs each
fold carries only ~50-70 pairs. A 6.5% difference cannot be resolved at that
sample size, which is what the rebuild plan predicted: "the current bottleneck is
the gold set, not the algorithm".

Two findings from this that are solid and do not depend on the gold set:

  1. THE ENCODER WAS NOT THE BOTTLENECK FOR THE BOUNDARY. mE5 separates gold pairs
     far better than production's mpnet — AUC 0.9082 vs 0.7994, measured on the
     same corpus and the same source text — and clustered F1 barely moved. Pairwise
     separation and boundary quality are not the same problem.
  2. THE ENTITY GRAPH'S JOB IS CANDIDATE GENERATION, NOT SIMILARITY. It proposes
     only 22 of 103 gold pairs DIRECTLY, yet yields recall 0.4563: over half its
     true positives come from transitivity. Embeddings cannot replace it — with
     ~0.1% of 14.6M pairs being true siblings, separating them needs a false
     positive rate near 1e-3, and AUC 0.91 is nowhere near that. The plan's premise
     that embeddings could carry L2 with entities demoted to a confirm is measured
     false for both encoders tried.


MEASURED 2026-09-03 AGAINST THE CORPUS SAMPLE — the first representative
numbers this project has had, and they change the picture the CJP slice gave:

                                CJP slice      corpus sample
    v1 (entity graph + Leiden)   F1 0.4541       F1 0.0508
    embedding distance ALONE     F1 0.3564       F1 0.6324
    embedding ROC-AUC               0.7994          0.9564

The CJP slice flattered v1 by roughly 9x and it is now clear why. Of 115
human-judged same-story pairs in the corpus sample, the v1 edge rule admits FOUR:

    gate rejecting the pair      CJP slice   corpus sample
    < 2 shared actors               21.4%        73.0%
    IDF weight < 0.30               51.5%        23.5%
    passes all three                21.4%         3.5%
    median shared actors               4            1

That is the whole thing. In a dense topic cluster a same-story pair shares four
actors; across the corpus it shares ONE, and `min_shared=2` is the foundation the
entire story graph is built on. Leiden never gets a chance — 96.5% of real pairs
have no edge to merge along, and no resolution or threshold reaches them.

Meanwhile the embedding is TIGHTER on exactly those pairs (median distance 0.377
vs 0.468 on CJP) and separates them cleanly at AUC 0.956. A single cosine
threshold — the crudest method available — beats the shipped system twelvefold.

Note the inversion: on the CJP slice embeddings LOSE to the entity graph (0.3564
vs 0.4541). Both facts are real. Entity overlap genuinely works inside one dense
topic and collapses outside it, which is why measuring on one topic cluster and
quoting it as story accuracy is the mistake gold_stories' own docstring warns
against, and why this file now carries both columns.


THE L2 REPLACEMENT, MEASURED 2026-09-03. Gate 1's condition is met on the corpus
sample, on both cross-validation folds:

    config: embedding kNN (k=5, d<=0.50) UNIONED with v1's entity edges at weight
            2.0, then the SAME Leiden CPM at resolution 0.20

                          corpus F1   corpus Cdet   CJP F1   max group
    v1 (entity edges)        0.0508        0.9739   0.4541          23
    v2 (union edges)         0.5930        0.5628   0.3793          17

    cross-validation, disjoint halves of the corpus gold stories
      fold A (15 stories)    0.0385 -> 0.6744      Cdet 0.9804 -> 0.4582
      fold B (15 stories)    0.0606 -> 0.5116      Cdet 0.9688 -> 0.6562

WHAT CHANGED IS THE EDGES, NOT THE ALGORITHM, and that is the finding. The plan
proposed replacing Leiden/CPM with agglomerative RAC. Measured, that is wrong:
every agglomerative configuration tried — average and complete linkage, union and
mutual kNN, k in 3..10 — blobbed catastrophically, max group 316 to 5,214 out of
5,413 events. The embedding space is a dense continuum and linkage chains through
it no matter how the connectivity is constrained. CPM was never the problem; it
is resolution-limit free and its resolution parameter is what holds group size at
17, inside Story Forest's bound of 25.

ENTITIES STAY, AS SECONDARY EVIDENCE. Pure embedding edges score 0.5731 on the
corpus and collapse the CJP slice to 0.1197. Adding the entity edges at weight
2.0 lifts CJP to 0.3793 and the corpus slightly too, to 0.5930 — the plan's
"embedding primary, entity confirm" earning its place rather than being assumed.

THE CJP REGRESSION IS REAL: 0.4541 -> 0.3793. It is the trade this whole
measurement exists to make legible. Entity overlap genuinely wins inside one
dense topic and collapses outside it, and the CJP slice is one dense topic by
construction. Its own docstring says never to quote it as story accuracy.

The winner sits on a shelf, not a spike: F1 stays 0.54-0.61 across resolution
0.15-0.25 and entity weight 1.5-3.0.

NOT SHIPPED. This is a measured recommendation for correlation/partition.py's
edge builder, not a change to it.
"""

from __future__ import annotations

import argparse
import gzip
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from tools.gold_stories import STORIES
from tools.score_stories import score_pairs

SNAPSHOT = Path(".cache/l2_snapshot.json.gz")
VECTORS = Path(".cache/l2_snapshot.npz")

DAY = 86400.0


@dataclass
class Snap:
    ids: list[str]
    index: dict[str, int]
    emb: np.ndarray          # (n, d), L2-normalised, so emb @ emb.T is cosine
    ts: np.ndarray           # (n,) epoch seconds; NaN where unknown
    titles: list[str]
    actors: list[list[str]]
    idf: dict[str, float]    # slug -> 1/df


def load() -> Snap:
    if not SNAPSHOT.exists():
        raise SystemExit(f"no snapshot at {SNAPSHOT} — run tools.snapshot_l2 first")
    with gzip.open(SNAPSHOT, "rt") as fh:
        d = json.load(fh)
    emb = np.load(VECTORS)["emb"]
    ts = np.array([np.nan if t is None else t for t in d["ts"]], dtype=np.float64)
    return Snap(
        ids=d["ids"],
        index={e: i for i, e in enumerate(d["ids"])},
        emb=emb,
        ts=ts,
        titles=d["titles"],
        actors=d["actors"],
        idf={k: 1.0 / v for k, v in d["df"].items() if v},
    )


# ── v1 reproduction ──────────────────────────────────────────────────────────

def entity_edges(
    snap: Snap, *, min_shared: int = 2, min_weight: float = 0.30, max_dist: float = 0.55
) -> list[tuple[str, str, float]]:
    """v1's edge rule, computed from the snapshot instead of SQL.

    Every event pair sharing >= min_shared person/org actors, weighted by the sum
    of 1/df over the shared ones, kept when that sum clears min_weight and the two
    embeddings sit within max_dist. Mirrors `_GRAPH_EDGES_SQL`.
    """
    postings: dict[str, list[int]] = defaultdict(list)
    for i, acts in enumerate(snap.actors):
        for a in acts:
            postings[a].append(i)

    shared: dict[tuple[int, int], list[float]] = defaultdict(list)
    for slug, evs in postings.items():
        w = snap.idf.get(slug)
        if w is None or len(evs) < 2:
            continue
        for x in range(len(evs)):
            for y in range(x + 1, len(evs)):
                shared[(evs[x], evs[y])].append(w)

    out: list[tuple[str, str, float]] = []
    for (i, j), ws in shared.items():
        if len(ws) < min_shared:
            continue
        w = float(sum(ws))
        if w < min_weight:
            continue
        if 1.0 - float(snap.emb[i] @ snap.emb[j]) > max_dist:
            continue
        out.append((snap.ids[i], snap.ids[j], w))
    return out


def baseline(snap: Snap, *, resolution: float = 0.020, content_gate: bool = True) -> dict[str, int]:
    """v1 end to end: IDF actor edges -> content gate -> Leiden CPM."""
    from correlation.partition import Node, filter_edges_on_content, leiden_partition

    nodes = {
        eid: Node(
            id=eid, title=snap.titles[i], sector=None, regions=[],
            occurred_at=None, source_count=1,
            actors={a: 1.0 / snap.idf[a] for a in snap.actors[i] if a in snap.idf},
        )
        for i, eid in enumerate(snap.ids)
    }
    edges = entity_edges(snap)
    if content_gate:
        edges = filter_edges_on_content(edges, nodes)
    return leiden_partition(nodes, edges, resolution)


# ── v2: embeddings first, time as a feature ──────────────────────────────────

def agglomerative(
    snap: Snap, *, threshold: float, tau_days: float | None = None,
    min_actor_idf: float = 0.0, knn: int | None = None,
) -> dict[str, int]:
    """Average-linkage agglomerative over embedding distance, optionally decayed.

    Agglomerative rather than a community detector because it has no resolution
    limit: it merges the closest pair at each step regardless of graph size, so one
    threshold can hold a 3-event story together and still split a 70-event blob.
    That is precisely what Fortunato & Barthelemy proved modularity cannot do.

    Average linkage, not single (which chains a whole corpus through one bridging
    pair) and not complete (which shatters a story whose first and latest
    development are legitimately far apart).

    TIME IS A FEATURE: sim' = sim * exp(-dt / tau) ranks a distant pair lower and
    never removes it. A pair with an unknown timestamp decays by nothing rather
    than by everything — absence of evidence must not cut.

    `min_actor_idf` is the secondary entity CONFIRM: a pair with no distinctive
    shared actor has its similarity damped, never zeroed. Default 0 leaves it off
    so the embedding-only result is measurable on its own.
    """
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform

    sim = (snap.emb @ snap.emb.T).astype(np.float64)
    np.clip(sim, -1.0, 1.0, out=sim)

    if tau_days:
        t = snap.ts
        dt = np.abs(t[:, None] - t[None, :]) / DAY
        dt[~np.isfinite(dt)] = 0.0      # unknown time => no decay, not total decay
        sim *= np.exp(-dt / tau_days)

    if min_actor_idf > 0:
        sim *= _actor_confirm(snap, min_actor_idf)

    dist = 1.0 - sim
    np.fill_diagonal(dist, 0.0)
    np.clip(dist, 0.0, None, out=dist)
    dist = (dist + dist.T) / 2.0        # linkage requires exact symmetry

    if knn:
        # CONNECTIVITY, without which this chains the corpus into blobs.
        #
        # Unconstrained average linkage over 5,413 events produced groups of
        # 638-1164 at every threshold that had any recall at all — an order of
        # magnitude past the Story Forest bound of 25. The embedding space is a
        # dense continuum, not a set of islands: news is full of near-duplicate
        # wire copy, so there is always some pair close enough to bridge two
        # stories, and average linkage will take it.
        #
        # Restricting merges to a k-nearest-neighbour graph is what the RAC
        # level-wise design (arXiv 2506.00277) actually specifies, and it supplies
        # the sparsity the entity graph gave v1 for free. Two events may only join
        # if one is among the other's k nearest — closeness alone is not enough.
        from sklearn.cluster import AgglomerativeClustering
        from sklearn.neighbors import kneighbors_graph

        conn = kneighbors_graph(snap.emb, n_neighbors=knn, mode="connectivity",
                                metric="cosine", include_self=False)
        conn = ((conn + conn.T) > 0).astype(np.int8)   # symmetric: mutual OR
        model = AgglomerativeClustering(
            n_clusters=None, distance_threshold=threshold, metric="precomputed",
            linkage="average", connectivity=conn,
        ).fit(dist)
        return {eid: int(model.labels_[i]) for i, eid in enumerate(snap.ids)}

    z = linkage(squareform(dist, checks=False), method="average")
    labels = fcluster(z, t=threshold, criterion="distance")
    return {eid: int(labels[i]) for i, eid in enumerate(snap.ids)}


def hybrid(
    snap: Snap, *, resolution: float = 0.020, tau_days: float | None = None,
    weight: str = "embed", min_weight: float = 0.30, max_dist: float = 0.55,
    knn: int = 0,
) -> dict[str, int]:
    """Entity graph for SPARSITY, embedding for the DECISION.

    This is the correction the measurements forced. The plan assumed embeddings
    could carry L2 alone, with entities demoted to a confirm. Two results say they
    cannot, at least not with this encoder:

      * Unconstrained average linkage produced groups of 638-1164 at any threshold
        with recall, and a kNN connectivity graph made it worse (max 5,334 of
        5,413) because a kNN graph over a dense corpus is ONE connected component
        and therefore adds no sparsity at all.
      * The arithmetic says why. Roughly 5,413 events across ~1,500 stories give on
        the order of 0.1% of the 14.6M possible pairs as true siblings. Separating
        that base rate needs a false-positive rate near 1e-3 at useful recall; the
        embedding's pairwise AUC is 0.8087. Good signal, nowhere near good enough
        to define a boundary unaided.

    What the entity graph actually supplies is not similarity — Nallapati is right
    that shared actors are a topic signal — it is CANDIDATE GENERATION. It cuts
    14.6M pairs to a sparse set with a workable base rate. So keep it for
    connectivity and let the embedding decide, which is the opposite assignment
    to v1: v1 weights those same edges by shared-actor IDF, i.e. it decides with
    the topic signal and merely gates on the embedding.

    `weight` picks what the community detector optimises over the same edges:
      idf     v1's behaviour — the shared-actor weight
      embed   embedding similarity (optionally time-decayed)
      product both, so an edge needs actors AND closeness to count
    """
    from correlation.partition import Node, filter_edges_on_content, leiden_partition

    nodes = {
        eid: Node(
            id=eid, title=snap.titles[i], sector=None, regions=[],
            occurred_at=None, source_count=1,
            actors={a: 1.0 / snap.idf[a] for a in snap.actors[i] if a in snap.idf},
        )
        for i, eid in enumerate(snap.ids)
    }
    edges = entity_edges(snap, min_weight=min_weight, max_dist=max_dist)
    if knn:
        # Union, not replacement. The entity graph and the embedding graph miss
        # different pairs: entity edges need two shared distinctive actors, which
        # cross-language coverage of one event often will not produce, while kNN
        # needs closeness, which a terse follow-up dispatch may not have. Either
        # alone leaves a component unconnected that the other would join.
        have = {(a, b) for a, b, _ in edges} | {(b, a) for a, b, _ in edges}
        edges = edges + [e for e in knn_edges(snap, knn, max_dist=max_dist)
                         if (e[0], e[1]) not in have]
    edges = filter_edges_on_content(edges, nodes)

    out: list[tuple[str, str, float]] = []
    for a, b, w in edges:
        i, j = snap.index[a], snap.index[b]
        sim = float(snap.emb[i] @ snap.emb[j])
        if tau_days:
            ta, tb = snap.ts[i], snap.ts[j]
            if np.isfinite(ta) and np.isfinite(tb):
                sim *= float(np.exp(-abs(ta - tb) / DAY / tau_days))
        if weight == "idf":
            out.append((a, b, w))
        elif weight == "embed":
            out.append((a, b, max(sim, 0.0)))
        else:
            out.append((a, b, w * max(sim, 0.0)))
    return leiden_partition(nodes, out, resolution)


def candidate_recall(snap: Snap, edges: list[tuple[str, str, float]], tag: str) -> None:
    """What fraction of gold same-story pairs the candidate set proposes DIRECTLY.

    NOT a recall ceiling, though it is tempting to read it as one. Clustering is
    transitive: an A-B edge and a B-C edge put all three in one group and recover
    A-C with no direct edge between them. Measured, v1's entity graph proposes only
    22 of 103 gold pairs directly (21%) while the partition it produces reaches
    recall 0.4563 — so more than half its true positives come from transitivity,
    not from an edge.

    Still worth printing: it separates "the similarity function ranked this pair
    badly" from "nothing ever put these two in the same component", which are
    different problems with different fixes.
    """
    from tools.gold_stories import pairs

    have = {(a, b) for a, b, _ in edges} | {(b, a) for a, b, _ in edges}
    pos = [(a, b) for (a, b), s in pairs().items() if s]
    hit = sum(1 for a, b in pos if (a, b) in have)
    print(f"  {tag:38} direct {hit}/{len(pos)} gold pairs ({hit / len(pos):.1%})"
          f"   edges {len(edges)}")


def knn_edges(snap: Snap, k: int, *, max_dist: float) -> list[tuple[str, str, float]]:
    """Mutual-kNN embedding edges: each event's k nearest, kept when mutual.

    MUTUAL, not one-directional. A hub event (a roundup naming twenty actors) is
    in hundreds of other events' neighbour lists while none of them is in its own;
    keeping those one-sided edges is how a kNN graph becomes one connected blob,
    which is exactly what happened when this was tried as a connectivity
    constraint (max group 5,334 of 5,413).
    """
    from sklearn.neighbors import NearestNeighbors

    nn = NearestNeighbors(n_neighbors=min(k + 1, len(snap.ids)), metric="cosine").fit(snap.emb)
    dist, idx = nn.kneighbors(snap.emb)
    near = {i: set(row[1:]) for i, row in enumerate(idx)}   # drop self
    out: list[tuple[str, str, float]] = []
    for i, js in near.items():
        for j in js:
            if j <= i or i not in near[j]:
                continue
            d = 1.0 - float(snap.emb[i] @ snap.emb[j])
            if d <= max_dist:
                out.append((snap.ids[i], snap.ids[j], 1.0 - d))
    return out


def _actor_confirm(snap: Snap, floor: float) -> np.ndarray:
    """1.0 where a pair shares a distinctive actor, slightly less where it does not.

    A damping factor, not a gate. Entities are a topic signal (Nallapati), so they
    may nudge a ranking and must not decide a boundary — and a hard actor gate
    would delete every cross-language pair, since two outlets in two languages
    rarely resolve to identical actor sets.
    """
    n = len(snap.ids)
    conf = np.full((n, n), 0.97)
    postings: dict[str, list[int]] = defaultdict(list)
    for i, acts in enumerate(snap.actors):
        for a in acts:
            if snap.idf.get(a, 0.0) >= floor:
                postings[a].append(i)
    for evs in postings.values():
        idx = np.array(evs)
        conf[np.ix_(idx, idx)] = 1.0
    np.fill_diagonal(conf, 1.0)
    return conf


# ── evaluation ───────────────────────────────────────────────────────────────

def structure(labels: dict[str, int]) -> dict:
    """Group-size shape. A pairwise win with a max group of 89 is not a win."""
    sizes = Counter(labels.values())
    multi = sorted(v for v in sizes.values() if v > 1)
    return {
        "groups": len(sizes),
        "multi": len(multi),
        "max": max(multi) if multi else 0,
        "mean": round(sum(multi) / len(multi), 2) if multi else 0.0,
        "over25": sum(1 for v in multi if v > 25),
    }


def folds(seed: int = 0) -> tuple[set[str], set[str]]:
    """Split the gold STORIES into two halves, deterministically."""
    import random

    keys = sorted(STORIES)
    random.Random(seed).shuffle(keys)
    half = len(keys) // 2
    return set(keys[:half]), set(keys[half:])


def line(tag: str, labels: dict[str, int], keys: set[str] | None = None) -> dict:
    s = score_pairs(labels, keys)
    st = structure(labels)
    print(
        f"  {tag:32} P {s['P']:.4f}  R {s['R']:.4f}  F1 {s['F1']:.4f}  "
        f"Cdet {s['Cdet']:.4f}  fp {s['fp']:<4} fn {s['fn']:<4} "
        f"| grp {st['multi']:<5} max {st['max']:<4} mean {st['mean']:<5} >25 {st['over25']}"
    )
    return s


def reembed(model: str, out: Path) -> None:
    """Re-encode the snapshot's SOURCE TEXT with another model, locally and free.

    The same text production embedded — the first chunk of each event's earliest
    article — so a difference in score is a difference in encoder and not in input.
    Encoding titles instead would have measured the text.

    Nothing is written to production. The representation swap this informs
    (plan step 3) would need a full re-embed there; this answers whether it is
    worth doing before anyone pays for it.
    """
    import os

    os.environ["PRISM_EMBED_MODEL"] = model
    from common.config import get_settings

    get_settings.cache_clear()
    from common.embeddings import embed_texts_sync

    snap = load()
    with gzip.open(SNAPSHOT, "rt") as fh:
        texts = json.load(fh)["text"]
    vecs: list[list[float]] = []
    step = 256
    for i in range(0, len(texts), step):
        vecs.extend(embed_texts_sync([t or " " for t in texts[i:i + step]]))
        print(f"    {min(i + step, len(texts))}/{len(texts)}", flush=True)
    mat = np.asarray(vecs, dtype=np.float32)
    n = np.linalg.norm(mat, axis=1, keepdims=True)
    n[n == 0] = 1.0
    mat /= n
    np.savez_compressed(out, emb=mat)
    print(f"  {model} -> {out}  shape {mat.shape} (snapshot has {len(snap.ids)} events)")


def gold_quantiles(snap: Snap) -> np.ndarray:
    """Distances between gold SAME-story pairs, for deriving a sweep range.

    Thresholds must come from the distribution the model actually produces, never
    from another model's scale. mpnet puts same-story pairs at median distance
    0.468; mE5 puts them at 0.157. A grid that suits one is pure noise on the
    other — a first sweep here reused L1's 0.12 neighbourhood and scored near-zero
    recall across the board, which looks like a clean negative result rather than
    a mis-specified experiment.
    """
    from tools.gold_stories import pairs

    same = [
        1.0 - float(snap.emb[snap.index[a]] @ snap.emb[snap.index[b]])
        for (a, b), s in pairs().items()
        if s and a in snap.index and b in snap.index
    ]
    return np.array(same)


def separation(snap: Snap, tag: str) -> None:
    """How well this representation separates gold same-story pairs from the rest.

    The number that decides whether an embedding can carry L2 at all. Reported
    with the distance quantiles because the operating THRESHOLD has to come from
    the distribution, not from another model's scale — a first sweep here ran
    0.15-0.45 borrowed from the L1 article-matcher and scored near-zero recall,
    because L2's positives sit around 0.47.
    """
    from tools.gold_stories import pairs

    same, diff = [], []
    for (a, b), s in pairs().items():
        if a in snap.index and b in snap.index:
            d = 1.0 - float(snap.emb[snap.index[a]] @ snap.emb[snap.index[b]])
            (same if s else diff).append(d)
    same, diff = np.array(same), np.array(diff)
    auc = float((same[:, None] < diff[None, :]).mean())
    print(f"  {tag:22} AUC {auc:.4f}   same median {np.median(same):.3f} "
          f"(p10 {np.percentile(same, 10):.3f}, p90 {np.percentile(same, 90):.3f})   "
          f"diff median {np.median(diff):.3f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline", action="store_true")
    ap.add_argument("--sweep", action="store_true")
    ap.add_argument("--cv", action="store_true")
    ap.add_argument("--reembed", metavar="MODEL")
    ap.add_argument("--vectors", metavar="NPZ", help="use these vectors instead of the snapshot's")
    ap.add_argument("--separation", action="store_true")
    a = ap.parse_args()

    if a.reembed:
        reembed(a.reembed, Path(a.vectors or ".cache/l2_alt.npz"))
        return

    snap = load()
    if a.vectors:
        snap.emb = np.load(a.vectors)["emb"]
        print(f"using vectors from {a.vectors}  shape {snap.emb.shape}")
    if a.separation:
        separation(snap, Path(a.vectors).stem if a.vectors else "production (mpnet)")
    gold = {e for v in STORIES.values() for e in v}
    missing = gold - set(snap.ids)
    print(f"corpus {len(snap.ids)} events, gold {len(gold)} events, missing {len(missing)}")
    if missing:
        raise SystemExit("gold set is not fully covered — every score would be on a slice")

    if a.baseline or not (a.sweep or a.cv or a.separation):
        print("\nv1 reproduced on THIS corpus (the number the rebuild must beat):")
        line("cpm 0.020 + content gate", baseline(snap))
        line("cpm 0.020, no content gate", baseline(snap, content_gate=False))

    if a.sweep:
        q = gold_quantiles(snap)
        grid = [round(float(np.percentile(q, pc)), 3) for pc in (25, 50, 65, 75, 85, 90)]
        gate = round(float(np.percentile(q, 97)), 3)
        print(f"\nthreshold grid from the gold same-pair distribution: {grid}")
        print(f"candidate-edge embedding gate (p97 of same-pairs): {gate}")

        print("\nagglomerative — embedding only, average linkage:")
        for th in grid:
            line(f"threshold {th:.3f}", agglomerative(snap, threshold=th))

        print("\nhybrid — entity graph for sparsity, embedding for the decision:")
        for w in ("idf", "embed", "product"):
            for res in (0.010, 0.020, 0.040):
                line(f"{w:<8} cpm {res:.3f}",
                     hybrid(snap, resolution=res, weight=w, max_dist=gate))
        print("\n...with time decay on the embedding term:")
        for tau in (7.0, 14.0, 30.0):
            for res in (0.020, 0.040):
                line(f"embed cpm {res:.3f} tau {tau:g}d",
                     hybrid(snap, resolution=res, weight="embed", tau_days=tau, max_dist=gate))

    if a.cv:
        fa, fb = folds()
        print(f"\ncross-validation: {len(fa)} / {len(fb)} gold stories per fold")
        cfgs: list[tuple[str, object]] = [("v1 baseline", lambda: baseline(snap))]
        for tau in (None, 7.0):
            for th in (0.25, 0.30, 0.35, 0.40):
                cfgs.append((
                    f"agglo th {th:.2f} tau {tau or '-'}",
                    lambda th=th, tau=tau: agglomerative(snap, threshold=th, tau_days=tau),
                ))
        for name, fn in cfgs:
            lab = fn()
            print(f"\n  {name}")
            line("  fold A (held out)", lab, fa)
            line("  fold B (held out)", lab, fb)


if __name__ == "__main__":
    main()
