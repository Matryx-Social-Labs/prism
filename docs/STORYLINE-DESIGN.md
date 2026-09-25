# Design: the storyline graph (events → stories → branches)

> **Historical proposal (2026-07-24)** — it became the story layer, with changes: the partitioner shipped as `CPMVertexPartition` (not `RBConfigurationVertexPartition`, which has the resolution limit), and the branch tree is served as provisional. Current behaviour: [PIPELINE §7](./PIPELINE.md#7-story-layer).

Status: proposal. Supersedes the on-read story graph in
[STORY-GRAPH.md](./STORY-GRAPH.md) once staged in. Author: correlation redesign,
2026-07-24.

---

## Context — why this redesign

"One story, every perspective" only works if Prism reliably decides **what is one
story** and **how a story branches**. Two capabilities depend on it:

1. **Perspectives** — every source's take on *one* event ("who is saying what").
2. **The storyline / branches** — the arc of a fast-moving story as it spreads. The
   canonical example, live right now: the **CJP protest at Jantar Mantar (Delhi)** is
   the root. It spread to a **Mumbai protest** (citizens out, Maharashtra politicians
   joining) — a *branch*. The Mumbai branch has its **own sub-events** (a politician
   joining, an org affected) — *sub-branches*. Other states escalate the same way.
   "Top stories" should show the **main storyline plus a summary of its branches**:
   which states are involved, which organisations/people are affected, who joined.

The current on-read graph ([STORY-GRAPH.md](./STORY-GRAPH.md)) has been patched
repeatedly (roundup exclusion, IDF weighting, an embedding gate, a generic-entity
stoplist) and each patch fixes one failure while another appears. The audits found
four failure modes it cannot all satisfy at once:

- **Generic-entity linking** (fixed by the stoplist, v0.0.65.0): the Assam flood
  pulled in the Sikkim tunnel collapse because both name `NDRF` / the `Army` /
  `Fire & Emergency` — responders on every disaster. `df` is low in a small corpus
  so IDF didn't suppress them, and a flood and a tunnel collapse embed *close*
  (0.457–0.504, under the 0.55 gate) — same "N dead, rescue ongoing" template.
- **Dual-topic bridge events** (unsolved): the Cauvery *water* story merges with TN
  *politics* because one genuine political-water article (EPS attacking Vijay over
  Cauvery) shares `Vijay`/`TVK`/`AIADMK` with the pure-politics events. Entity
  overlap, embedding, and modularity all say "connected" — because textually they
  are. Only *semantic coherence* separates them.
- **Consistency** (unsolved): the "story so far" changes depending on which
  development you enter from. Jumping between CJP developments gave Jaccard
  0.24–0.64 (losing 3–8 developments). Root cause: the seed-relative embedding gate
  makes the *component* entry-dependent, and `_seed_community`'s per-seed modularity
  split makes the *community* entry-dependent too.
- **Over-merge / blobs**: connected components over "close enough" edges drift
  transitively into 53- and 105-event blobs; `greedy_modularity_communities` can't
  cut them cleanly.

The root problem: **one flat community-detection pass is doing three different
jobs.** The literature treats them as three layers, with a different right tool for
each. This document specifies that three-layer model.

---

## The three layers

```
articles ─(L1 same-event)→ EVENT ─(L2 boundary)→ STORY ─(L3 coherence)→ branch tree
          MinHash-LSH +            Leiden                coherence + causal LLM
          HDBSCAN / cascade        (well-connected)      (root → branch → sub-branch)
```

| Layer | Question it answers | Right tool | Failure it fixes |
|---|---|---|---|
| **L1 Event** | which articles are the *same event* (perspectives) | MinHash-LSH near-dup + HDBSCAN density cluster (or keep the cascade) | cross-language fragments |
| **L2 Story boundary** | which events belong to *one storyline* | **Leiden** community detection | 53-blob, over-merge, badly-connected |
| **L3 Branch tree** | how the story *branches* (root → sub-branches) | **coherence**-scored directed graph + causal LLM link | Cauvery dual-topic; builds the tree |

Each layer is independently shippable and testable. L1 and L2 are pure-local (no
LLM). L3's coherence score is local; its optional causal confirmation is the one
piece that wants LLM credits.

---

## Layer 1 — Event: same-event clustering (perspectives)

**Job:** collapse the fifty outlets covering one real event into one canonical event,
so the story view can show every source's stance ("who is saying what"). This is the
classic *Topic Detection and Tracking* unit ([TDT with time-aware embeddings][tdt]).

**Today** (`correlation/clustering.py`, `correlation/consumer.py`): a match cascade —
CVE id → resolved URL → title+time → entity+time → embedding (< ~0.12). Clean below
0.12 (an audit found zero unmerged sub-threshold pairs), but it fragments a few
**cross-language** same-event pairs: a Hindi and an English headline of one story
embed ~0.13 (just over 0.12), so "यूपी फ्री स्कूटी" and "UP cabinet approves free
scooty" become two events.

**Proposed:** the production TDT recipe ([Chronicle][chronicle]) —
**MinHash-LSH** near-duplicate dedup + **HDBSCAN** density clustering. HDBSCAN needs
no fixed threshold (the 0.12 cliff is what splits cross-language pairs), models
clusters as dense regions, and flags outliers instead of forcing them. Cross-language
merging also benefits from title-translation or a language-agnostic key. This is the
lowest-priority stage — the cascade is *mostly* right — but it removes the last
fragmentation edge case.

---

## Layer 2 — Story boundary: which events form one storyline

**Job:** given the event graph (nodes = events, edges = shared distinctive actors),
find the set of events that belong to one storyline — the boundary, not yet the
internal branch structure.

**Today:** an on-read BFS component (`_story_component`) + `greedy_modularity_
communities` (`_seed_community`). Two flaws: the BFS is *entry-dependent* (breaks
consistency), and greedy modularity produces badly-connected/oversized communities
— [From Louvain to Leiden][leiden] measured **up to 25% badly-connected and 16%
disconnected** communities from this class of algorithm. That is our 53-event blob.

**Proposed:** **Leiden** ([leidenalg + igraph][leidenalg]), computed **globally and
once** (not per-read). Leiden *guarantees* well-connected communities, is ~20×
faster, and exposes a resolution parameter to tune story granularity. Edge rules stay
as hardened: shared non-stoplisted person/org actors ≥ 2, IDF-weighted (`sum 1/df`)
≥ floor, embedding coherence, roundups excluded (all already in `threads.py`:
`STORY_STOP_ENTITIES`, `_ROUNDUP_CTE`, `STORY_MIN_EDGE_WEIGHT`, `STORY_MAX_EMBED_DIST`).

```python
import leidenalg, igraph
part = leidenalg.find_partition(
    g, leidenalg.RBConfigurationVertexPartition, weights="weight", resolution_parameter=r
)
```

Because the partition is computed once and stored (Layer 3 persistence), every
development of a story reads the same boundary — **consistency by construction**.

---

## Layer 3 — Branch tree: root → branches → sub-branches

This is the new capability and the crux of the product vision. A story is not a flat
set; it is a **rooted, branching graph** — a "metro map" ([Shahaf, Guestrin &
Horvitz, *Metro Maps of Information*][metromaps]; [*Trains of Thought*][trains]).
Complex stories "spaghetti into branches, side stories, and intertwining narratives";
each *line* is a coherent narrative thread and lines *intersect* at shared events.

### The coherence metric (the missing signal)

Modularity only sees edge **density**, which is why it merged Cauvery-water into the
dense TN-politics cluster. Shahaf's **coherence** asks a different question: *do the
same distinctive actors persist along the chain, or does it jitter between themes?*

- **CJP → Mumbai → Maharashtra**: `Cockroach Janta Party` + the protest actors
  persist across every hop → **coherent** → one storyline with branches.
- **Cauvery → Mekedatu → TVK-budget**: the persisting actor set *turns over* — water
  bodies at hop 1, budget actors at hop 2 → **jitter** → not one story, even though
  each edge is dense. Coherence rejects it; modularity did not.

Operationally, for a candidate branch edge `parent → child` inside a Leiden story:

```
coherence(parent, child) =
    idf_weight( distinctive actors shared by child AND the story SPINE )
    × temporal_ok(parent, child)          # child not strictly before parent
    × embedding_coherence(child, root)     # child close to the ROOT, not just parent
```

where the **spine** is the set of high-salience, low-df actors of the root/main event.
Anchoring on the *root spine* (not the immediate neighbour) is what stops one-hop
drift through a dual-topic bridge: Mekedatu shares the water spine with the root;
TVK-budget shares none of it.

### Building the tree

Within each Leiden story:

1. **Root** = the most-central event: highest source_count (most-corroborated), then
   earliest `occurred_at`, then lowest id (deterministic). This is the "main event".
2. **Spine** = the root's distinctive actors (+ actors shared across many members).
3. **Branch attachment** = a maximum-coherence spanning **arborescence** rooted at the
   main event: attach each event to the prior event with which it has the highest
   `coherence`, respecting time. This yields root → branch → sub-branch nesting
   directly (Mumbai attaches to the Delhi root; "Aditya Thackeray joins" attaches to
   the Mumbai branch).
4. **Optional causal confirmation** — the existing LLM thread-link
   (`link_event_threads` → `event_links` `leads_to`/`related`) run *only on the
   coherence-shortlisted edges*, to label a branch as **caused-by** vs merely
   concurrent and to veto a semantically-wrong merge (the Cauvery case). Coherence
   pre-filtering makes this a handful of LLM calls per story, not O(n²).

### What the reader sees

- **Perspectives** = Layer 1 (the event's sources by stance).
- **Story so far** = the branch tree from the root — identical from every node.
- **Top stories** = the root + a generated **branch summary**: "spreading to Mumbai
  and Pune; Maharashtra NCP(SP) leaders joined; Delhi Metro disrupted" — the metro-map
  summary of the sub-branches (other states, orgs, people involved).
- **Escalation elsewhere** = a new state's protest attaches as a branch by coherence +
  temporal succession + a `leads_to` causal edge.

---

## Data model

Additive, no rewrite of existing tables:

- `events.story_id UUID NULL` (indexed) — the Leiden story a development belongs to.
- `events.branch_parent_id UUID NULL` — the parent event in the branch arborescence
  (`NULL` for a story root). The tree is `(story_id, branch_parent_id)`; the root is
  the member whose `branch_parent_id IS NULL`.
- Reuse `event_links` (already exists) for LLM-confirmed `leads_to`/`related` causal
  labels on branch edges.
- Optionally a `storylines` table (like the trending `stories` table) holding the
  root, spine actors, involved regions/orgs, and a generated branch summary for the
  "top stories" surface.

A periodic **partitioner** (worker loop, off ingest — mirrors
`correlation/trending.py::reconcile_stories`) recomputes `story_id` + the branch tree
over the recent window. `story_id` is stable across runs (reuse the lowest existing id
in a group). Serving reads the stored tree — no BFS on read; identical from every
development.

---

## Serving

`story_timeline(event)` and `GET /api/v1/events/{id}` change from an on-read BFS to a
stored lookup: `SELECT ... FROM events WHERE story_id = :sid`, then order by the
branch tree. Falls back to the current BFS for events not yet partitioned. The
`EventDetail.story` shape (`{developments[], cast[]}`) gains a `branches` structure
(root + nested children) so the frontend can render the tree, and the trending/top-
stories surface reads the storyline summary.

---

## Algorithms & libraries

| Need | Library | Notes |
|---|---|---|
| Community boundary | `leidenalg` + `python-igraph` | guarantees connected communities; resolution knob |
| Density event cluster | `hdbscan` | no fixed threshold; outlier detection |
| Near-dup dedup | `datasketch` (MinHash-LSH) | cross-language same-event |
| Coherence + arborescence | in-repo (numpy/networkx) | spine-anchored coherence, max-coherence tree |
| Causal confirmation | existing `link_event_threads` | LLM; runs on shortlisted edges only |

---

## Staging (each independently shippable)

1. **Leiden swap** (local) — replace `greedy_modularity_communities` with `leidenalg`
   for the story boundary. Validate CJP/Cauvery/Assam stay clean; measure blob sizes.
2. **Coherence metric** (local) — spine-anchored coherence to keep/cut branch links.
   This is what finally separates Cauvery-water from TVK-budget without the LLM.
3. **Persist** (local) — `story_id` + `branch_parent_id` + the periodic partitioner →
   consistency by construction + heavy logic off the read path.
4. **Branch tree + summary** — build the arborescence, expose `branches` in the API,
   generate the top-stories branch summary.
5. **HDBSCAN + MinHash-LSH** (local) — tighten Layer 1 same-event grouping / cross-
   language dedup.
6. **LLM causal confirmation** (needs credits) — `link_event_threads` on shortlisted
   edges for `caused-by` labels and semantic vetoes; the quality ceiling.

Recommended first cut: **1 + 2 + 3** — local, no credits, fixes the contamination
*and* the consistency, and lays the persistence for the branch tree.

---

## Validation

Grounded, reproducible cases (run the partitioner against a prod snapshot, read-only,
before/after):

- **Consistency**: for each development of the CJP story, the timeline set is
  identical (Jaccard 1.0). Today it is 0.24–0.64.
- **Contamination**: the Assam flood story contains no Sikkim events (fixed); the
  Cauvery water story contains no TVK-budget / housing-board events (Stage 2 target).
- **Branch correctness**: the CJP root has a Mumbai branch; the Mumbai branch has the
  Maharashtra-politician sub-events under it; Delhi-metro-disruption attaches to the
  root.
- **No over-merge**: no story exceeds a sane size without a coherent spine (the 53/105
  blobs disappear).
- **No fragmentation**: cross-language same-event pairs (dengue vaccine, UP scooty)
  land in one event (Stage 5) or at least one story.

Metrics logged by the partitioner: story count, size distribution, changed-count,
mean intra-story coherence.

---

## Risks & open questions

- **Leiden resolution** is a knob; too high over-splits CJP, too low re-merges. Tune
  against the validation cases; consider per-story resolution by size.
- **Coherence spine** definition needs empirical tuning (how many spine actors, df
  ceiling for "distinctive"). Start from the observed numbers (CJP core df 50–82;
  Delhi Police df 6 carried edges; generic responders df 2–4 are stoplisted).
- **Backfill**: the partitioner assigns `story_id` forward; a one-time pass covers the
  recent window. Historical events beyond the window stay on the BFS fallback.
- **Cost of the LLM stage** depends on shortlist size; coherence must prune hard.
- **Small-corpus IDF** still under-suppresses generic entities until volume grows; the
  stoplist bridges that, and Leiden + coherence reduce the blast radius.

---

## References
- Shahaf, Guestrin, Horvitz — *Metro Maps of Information* ([PDF][metromaps], [ACM][metroacm]); *Trains of Thought: Generating Information Maps* ([PDF][trains]).
- *Hierarchical Storyline Generation Based on Event-centric Temporal Knowledge Graph* ([Springer][hsg]).
- Traag, Waltman, van Eck — *From Louvain to Leiden: guaranteeing well-connected communities* ([Nature][leiden], [arXiv][leidenarxiv]); [leidenalg docs][leidenalg].
- *Topic Detection and Tracking with Time-Aware Document Embeddings* ([arXiv][tdt]).
- *Chronicle* — MinHash-LSH + HDBSCAN news event pipeline ([GitHub][chronicle]).
- *LLM-Enhanced Clustering for News Event Detection* ([arXiv][llmclust]).

[metromaps]: https://www.hyadatalab.com/papers/shahaf-maps.pdf
[metroacm]: https://dl.acm.org/doi/10.1145/2451836.2451840
[trains]: https://www.cs.cmu.edu/~dshahaf/fp0590-shahaf.pdf
[hsg]: https://link.springer.com/chapter/10.1007/978-981-19-3610-4_11
[leiden]: https://www.nature.com/articles/s41598-019-41695-z
[leidenarxiv]: https://arxiv.org/abs/1810.08473
[leidenalg]: https://leidenalg.readthedocs.io/en/latest/intro.html
[tdt]: https://arxiv.org/pdf/2112.06166
[chronicle]: https://github.com/dukeblue1994-glitch/chronicle
[llmclust]: https://arxiv.org/pdf/2406.10552
