# How stories form and stay coherent

> **Historical (2026-07-30).** This describes the on-read story graph as it was built in July. The story layer now runs Leiden (CPM) over a mutual-kNN graph in `correlation/partition.py` and reconciles stories in `correlation/trending.py`; the trending same-story rule is an IDF-weighted cast sum, not "≥ 3 shared cast members". Current behaviour: [PIPELINE §7](./PIPELINE.md#7-story-layer). Measurements: [ML-EVALUATION §4.1](./ML-EVALUATION.md).

Prism's core claim is "one story, every perspective." That only works if the
system reliably decides **what is one story** — collapsing fifty duplicate
headlines about one real event into a single canonical event, then stitching the
related events of a fast-moving story into one timeline, without dragging in
unrelated news. This document explains how that happens and why the design is
what it is. For the tables, see [DB-SCHEMA.md](./DB-SCHEMA.md); for the pipeline
stages, see [ARCHITECTURE.md](./ARCHITECTURE.md).

There are four layers, each solving a different grouping problem:

```
articles ──cluster──▶ canonical events ──story graph──▶ story timeline
                             │                                │
                             └──────────── trending ──────────┴──▶ persistent stories
```

---

## 1. Clustering: articles → one canonical event

Fifty outlets covering the same reservoir decision must become one event, not
fifty. `correlation/` matches each incoming enriched article against existing
events through a **cascade**, cheapest and most certain first:

1. **CVE id** — exact, for cyber records.
2. **Resolved URL** — the same canonical link.
3. **Title + time** — near-identical headline within a time window.
4. **Entity + time** — shared extracted actors within a window.
5. **Embedding** — cosine distance under the clustering threshold (~0.12).

The article joins the first event it matches; if none, it seeds a new event. The
correlation consumer runs at **concurrency 1** on purpose: two articles for the
same real event arriving in parallel would otherwise race match-or-create and
split the cluster.

**The lesson that shaped this (from the CVE work):** identity matching, not fuzzy
similarity, is what keeps clusters clean. Over-eager fuzzy matching once merged
1,638 distinct CVE records into 7. Records cluster by identity (the CVE id);
news clusters by the cascade above, with embedding as the last resort, not the
first.

---

## 2. The event projection

Once an article joins an event, the consumer rebuilds the event's **projection**
(`correlation/consumer.py::_rebuild_projection`) — the denormalized JSON the
serving layer reads without touching the raw tables. It carries:

- **Perspectives** (Both Sides) — the competing narratives grouped by stance,
  each with outlet origin and funding transparency.
- **Impacts** (So What) — the affected entities and second-order effects.
- **`headlines[]`** — the best headline per language, so the feed can serve a
  reader their preferred language (falling back to English, never hiding a story).
- **`languages[]`** — which languages the story is covered in.
- **Cast / entities** — the persons and organizations extracted from the members.

Language is not a lens: it ranks and localizes the feed, it never filters it. A
Hindi-primary reader and an English-primary reader see the same set of stories,
each with the headline in their language when it exists.

---

## 3. The story timeline

A single event is one moment; a *story* is the arc — the Wangchuk hospital
transfer, the Mumbai solidarity protest, the parliamentary walkout, all one
protest story. `correlation/threads.py::story_timeline(event_id)` computes, on
read (cached 300s in Redis), the connected component of the seed event over a
graph of **shared-actor edges**, then splits it into topical sub-stories by
community detection.

**Only the story page serves this arc.** `GET /api/v1/trending/{slug}` builds it
with the sibling `story_timeline_from_members(...)` over the story's *frozen*
`member_event_ids`; the event detail route used to serve it too, via
`story_timeline(event_id)` over the *live* partition. Two member sets for one
story means the two pages could legitimately disagree about which developments
exist — so the arc has one owner now, and `GET /api/v1/events/{id}` returns no
timeline at all. `story_timeline(event_id)` remains the primitive the partition
work and its tests are written against.

The edge between two events is:

```
weight = sum(1/df) over shared person/org actors  ×  exp(-λ · days_apart)
```

Four mechanisms keep this from either fragmenting a real story or fusing unrelated
ones. Each was validated against live data (the CJP/NEET protest and a Cauvery
water dispute), because the failure modes are only visible at real scale.

### IDF weighting, not a df cutoff
A shared *magnet* actor (one that appears on dozens of events — "Cockroach Janta
Party" at df 82 → 1/df 0.012) contributes almost nothing to an edge, while a
*specific* actor ("Delhi Police" at df 6 → 0.167) carries it. We deliberately do
**not** exclude high-df actors: a huge trending story's own core is high-df (CJP
82, Pradhan 76, Wangchuk 50), and a df cutoff deleted exactly those and shattered
the story into orphans. Down-weight the magnets and let structure separate stories
— a magnet bridges communities weakly; a real story's core co-occurs densely. A
`min_shared = 2` floor drops single-actor noise; a `min_edge_weight = 0.15` floor
drops magnets-only pairs.

### Roundup / live-blog exclusion
Daily digests ("Tamil Nadu Today: …") and live-blogs ("… LIVE:") pack dozens of
unrelated actors into one body, so they bridge everything — a single "Tamil Nadu
Today" mentioning an ammonia leak *and* Cauvery *and* a party budget stitches all
three together. They are excluded from the story graph when a **title marker**
(`today:`, `live:`, `digest:`, …) coincides with a **high entity count (≥8)**.
The entity floor is the trick: it keeps single-topic items like "IndusInd Q1
Results Today:" (few entities) in the graph and never touches real big stories,
which carry no marker.

### Seed-relative topical coherence
Shared actors alone aren't enough. A genuine dual-topic event — "CM Vijay reviews
Mekedatu" is both a Cauvery dam story *and* a Vijay political act — is close to the
water seed yet also close to Vijay's unrelated politics, so an edge-relative gate
leaks the whole political cluster in one hop. The fix is a **seed-relative**
embedding-distance ceiling (cosine ≤ 0.55): every member must be topically close
to the *seed*, not merely to its neighbour. On live data a story's real members
sit ≤ 0.47 from the seed while contamination sits ≥ 0.62, and cross-state branches
of one protest (Delhi ↔ Mumbai, 0.37) stay well inside the gate. A raised IDF bar
can't do this job — it would also drop the high-df magnets that hold a mega-story
together.

### Community detection
The connected component can still span closely-related sub-stories linked by a few
bridge actors (an Iran war and a Lebanon peace track). Greedy modularity cuts the
weak bridges so each development shows its own tight arc; it falls back to the whole
set when there are no edges (a single-source story) or the seed lands nowhere.

**Why these four together:** they let the same threshold keep a Delhi protest and a
same-cause Mumbai protest in one story (distinctive shared cause/actors, close
topic) while dropping a water story's accidental link to a party budget (ubiquitous
shared politician, far topic). That is the extra-vs-missing-coverage tension
resolved by structure and topic, not by a single global knob.

---

## 4. Trending

Trending promotes hot stories to durable, shareable identities. `correlation/
trending.py` runs a reconciler off the ingest path (every ~10 min in the worker):

1. **Candidate events** — ranked by **velocity**: distinct *new* news-outlet slugs
   in the last 6 hours (CVE feeds excluded, so a backfill or one chatty source
   can't fake a trend), decayed by recency.
2. **Communities** — group candidates into stories and compute each one's facts
   (cast, sources, hero, regions).
3. **Dedup** — two communities are the same story when member-overlap ≥ 0.6, **or**
   cast Jaccard ≥ 0.5, **or** they share ≥ 3 cast members outright. The layered
   test exists because `story_timeline`'s 30-event cap fragments a >30-event
   cluster (all of CJP) into different member subsets per seed, so member-overlap
   alone splits one mega-story into six near-duplicate cards; protagonists are
   stable even when the member window shifts.
4. **Reconcile to persistent `stories`** — match each community to existing stories:
   0 matches → **create** (frozen slug from the cast), 1 → **update** (slug and id
   persist), ≥2 → **merge** (oldest `first_seen` wins; the others get
   `merged_into` and go dormant). A **self-healing** union-find pass also collapses
   existing active stories that are the same story as each other, so duplicates
   created before a dedup improvement converge on the next pass rather than
   lingering for the 24h dormant timer.

**Why persistent stories:** a trending card is shareable (`/trending/<slug>` with
an auto-generated OG image), so its URL must be stable. Slugs are **frozen** at
creation; a merged story's slug redirects to the canonical one (`canonical_slug`)
so an old link never breaks; and stories go **dormant, never deleted**, so a
shared link keeps resolving after the story cools.

---

## 5. Lens briefs

The story timeline and projection are lens-agnostic. The **lens brief** is where a
story is re-read for a role: on demand, per `(event, lens)`, one LLM call generates
the "what this means for you" analysis, cached on the projection and single-flighted
across replicas so a burst of viewers costs one call. Switching the lens on a story
swaps the brief — the signature "same story, changed meaning" moment. The set of
lenses is declarative (`common/lenses.py`); a new role is a new lens on this same
backbone, never a new pipeline.

---

## Where the code lives
| Concern | File |
|---|---|
| Clustering cascade | `correlation/consumer.py`, `correlation/clustering.py` |
| Event projection | `correlation/consumer.py::_rebuild_projection` |
| Story timeline graph | `correlation/threads.py` (`story_timeline`, `_story_component`) |
| Trending | `correlation/trending.py` (`detect_trending_communities`, `reconcile_stories`) |
| Lens definitions | `common/lenses.py` |
| Lens brief generation | `correlation/briefs.py`, `api/routes/events.py` |

## Related
- [ENRICHMENT-SCHEMA.md](./ENRICHMENT-SCHEMA.md) — what extraction produces per article.
- [DB-SCHEMA.md](./DB-SCHEMA.md) — events, event_entities, stories, stream topics.
- [API.md](./API.md) — how the timeline and trending are served.
