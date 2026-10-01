# Event canonicalization — one happening, one event

The first step of the funnel. Every article that passes the gate and extraction is
either **attached to an existing event** (the same real-world happening) or
**founds a new one**. Stories, trending, coverage counts and briefs are all built
on events, so a missed attachment shows up everywhere downstream: one death
becomes thirteen cards, a story reads "1 outlet" when twelve covered it, and the
story layer has to stitch fragments it should never have received.

This document is the reference for how that decision is made, what was measured,
and how to change it safely. Code: `correlation/clustering.py` (the cascade),
`correlation/verify.py` (the verified tier), `correlation/consumer.py` (attach).
Measurements were made on 2026-09-25 against production data; the harnesses are
in `tools/` and every number below says where it comes from.

- [What an event is](#what-an-event-is)
- [The match cascade](#the-match-cascade)
- [What went wrong (audit, 2026-09-25)](#what-went-wrong-audit-2026-09-25)
- [What each article carries, and what separates duplicates](#what-each-article-carries-and-what-separates-duplicates)
- [The verified tier](#the-verified-tier)
- [Cost and latency](#cost-and-latency)
- [Rollout](#rollout)
- [Datasets](#datasets)
- [How to measure](#how-to-measure)
- [Open work](#open-work)
- [References](#references)

## What an event is

**The same real-world happening**: the same incident, death, match or race, ruling,
announcement, deal, statement or protest — even when one report adds details,
gives different figures, arrives later or is in another language.

Not the same event (founder decision, 2026-09-25):

| Not the same happening | Where it goes |
|---|---|
| a follow-up or reaction ("stars pay tribute" after "actor dies") | its own event, grouped at the **story** layer |
| an earlier or later stage (forecast vs aftermath, semifinal vs final) | its own event, same story |
| a different person's statement on the same issue | its own event |
| another instance of a recurring kind (another co-op's results, another district's Lok Adalat, another day's prices or weather) | its own event, often no shared story |

This is the definition the labellers use (`label_batches.notes` for kind
`event_identity`) and the one Jev is asked, word for word (`correlation/verify.py:SAME_HAPPENING`).

## The match cascade

`correlation/clustering.find_event` tries tiers strongest-first and takes the
first match. The trail is kept on `event_memberships.match_type`.

```mermaid
flowchart TD
    A[enriched article] --> CVE{shared CVE id?}
    CVE -- yes --> M1[attach: cve_id]
    CVE -- no --> REC{authoritative CVE record?}
    REC -- yes --> NEW[found a new event]
    REC -- no --> URL{same canonical URL<br/>already in an event?}
    URL -- yes --> M2[attach: url_exact]
    URL -- no --> TT{title trigram >= 0.6<br/>within 4 days?}
    TT -- yes --> M3[attach: title_time]
    TT -- no --> HL{English headline cosine<br/>>= threshold? — OFF}
    HL -- yes --> M4[attach: headline_xlang]
    HL -- no --> EMB{trusted script AND body<br/>embedding distance <= 0.050?}
    EMB -- yes --> M5[attach: embedding]
    EMB -- no --> ENT{shared IDF-weighted actors<br/>inside the loose band?}
    ENT -- yes --> M6[attach: entity_overlap]
    ENT -- no --> V{PRISM_EVENT_VERIFY on?}
    V -- no --> NEW
    V -- yes --> G[nearest member articles by gist,<br/>distance <= 0.10, up to 5 events]
    G -- none --> NEW
    G --> J[one Jev call: same happening?<br/>vs each event's founding headline + summary]
    J -- "max noul >= 0.85, live" --> M7[attach: verified]
    J -- "below, shadow, error or timeout" --> NEW
```

Distances are cosine distances on `intfloat/multilingual-e5-base`; they move with
the model and live in one table, `correlation/clustering._SCALE`.

## What went wrong (audit, 2026-09-25)

**One death, thirteen events.** Mushtaq Khan's death on 2026-09-24 produced 13
events from 22 articles in six languages. NDTV alone founded three; two events
carried byte-identical Prism headlines ("Bollywood actor Mushtaq Khan dies at age
56"). The hockey match India beat Sri Lanka 16–1 was two events ("India lead Sri
Lanka…", 1 source; "India men's hockey team records big win…", 5 sources).

Why each article missed every tier:

| Tier | Why it could not match |
|---|---|
| title_time | compares the **outlet's** raw title with the event's **Prism** English headline — two voices; a Hindi, Odia or Urdu title can never match. Fires on ~1% of articles |
| headline_xlang | exists, **off** (threshold 0) — no labels to set it from |
| embedding | the event's vector is its founder's first 1200 raw characters, near-duplicates only (≤ 0.050), and Odia/Assamese/Urdu/Marathi are not trusted scripts |
| entity_overlap | needs ≥ 2 shared person/organisation actors; soft news extracts one ("Mushtaq Khan") |

**Across the corpus.** 7 days, 11,193 events with Prism headlines: 85% hold a
single article, and ~75% of all articles found a new event — a rate that has held
since at least late August, so it is chronic, not a regression. Judged the way the
verified tier decides (`tools/audit_event_dups`, founder-anchored):

| Jev floor | Copies | Share of events | Groups | Largest group |
|---|---|---|---|---|
| 0.85 | 1,118 | **10.1%** | 756 | 9 |
| 0.70 | 1,674 | 15.2% | 1,058 | 11 |

A random sample of 20 merges at ≥ 0.85 was 20/20 correct (week run,
2026-09-25).

**Replayed through the real cascade** (`tools/score_cascade`, all 794 labelled
pairs — July gold, batch 3 and silver — 922 events re-decided against a copy of
production, mE5, 2026-09-25), today's matcher keeps what it merges and misses
almost everything else:

| Cascade | Pairs | TP | FP | FN | Precision | Recall | F1 |
|---|---|---|---|---|---|---|---|
| current (no verified tier) | 794 | 30 | 3 | 136 | 0.909 | **0.181** | 0.302 |
| + verified tier at 0.85 | 794 | 89 | 5 | 77 | **0.947** | **0.536** | **0.685** |

By set — the gain is not one set's:

| Set | Current P / R | With the verified tier P / R |
|---|---|---|
| July gold (398 pairs) | 0.964 / 0.458 | 0.969 / 0.525 |
| batch 3, cross-language (268) | — / **0.000** | 0.875 / **0.488** |
| silver, same-language (128) | 0.750 / 0.047 | 0.974 / 0.578 |

711 Jev calls for the whole replay (about $0.03). Read the silver row with care:
its labels are Claude's and unratified, and the 0.85 floor was chosen partly on
it; July gold is the cleanest held-out evidence, and it moved in the same
direction without losing precision. Linking the same pairs **transitively** (union-find) instead chained
a week of Trump–Xi coverage (itinerary, airport arrival, the meeting) into one
46-event group at 0.7 — which is why an article is only ever judged against an
event's founder.

## What each article carries, and what separates duplicates

Everything below is stored for every article at ingest (`docs/PIPELINE.md`). Each
signal was scored as a same-happening classifier on three labelled sets
([Datasets](#datasets)): **silver** (128 same-language September pairs sampled
from real candidates, including the templated-news traps), **batch 3** (268
cross-language pairs, two labellers) and **July gold** (398 pairs, mostly English).
AUC 1.0 separates perfectly, 0.5 is chance.

| Signal | Stored in | Silver | Batch 3 | July gold |
|---|---|---|---|---|
| **Gist**: mE5 over the extractor's English headline + one-line summary | `articles.gist_embedding` (new) | **0.913** | **0.992** | **0.940** |
| Same, bge-small-en (English-only model) | — | 0.907 | 0.991 | 0.953 |
| English headline, IDF word cosine | `enrichments.shared_fields.headline` | 0.802 | 0.976 | — (no English headlines in July) |
| English headline + summary, IDF word cosine | shared_fields | 0.873 | 0.979 | 0.928 |
| Raw body, first chunk (what the embedding tier uses) | `article_chunks` | **0.456** | 0.956 | 0.832 |
| Raw body, mean of chunks | `article_chunks` | 0.437 | 0.914 | 0.758 |
| Body 5-gram shingle Jaccard | `articles.clean_text` | 0.361 | 0.509 | 0.718 |
| Shared people/organisations (Jaccard) | shared_fields.entities | 0.702 | 0.874 | 0.805 |
| Places / numbers / occurred-on agree | shared_fields | 0.63–0.68 | 0.66–0.74 | 0.62–0.75 |
| Same photo (dHash), same publisher | `raw_items.image_phash` | ~0.5 | ~0.5 | ~0.5 |
| **Jev**, "same happening?" on headline + summary | — | **0.993** | **0.985** | **0.964** |
| Jev + reader brief | — | 0.990 | 0.985 | 0.964 |
| Jev + the article's opening 700 characters (original language) | — | 0.993 | 0.983 | 0.952 |

What this says:

- **The article text is used — through the extractor.** Extraction reads up to
  12,000 characters of the article and writes an English headline and summary for
  every article in every language. Embedding that distilled English beats
  embedding the raw text everywhere, and by the widest margin exactly where it
  matters: on hard same-language pairs the raw body is *worse than chance*.
- **Why the raw body fails.** Site furniture: 19% of the first 200 words of a
  Prajavani article (a quarter of the corpus), 14% of Amar Ujala's and 13% of Aaj
  Tak's are 5-grams repeated across ≥ 10 of the same outlet's articles in a week.
  And templated local news reads alike ("… Cooperative Society held its annual
  general meeting …").
- **Adding text to the judge does not help.** The brief and the article's opening
  add tokens and no accuracy.
- **Hand-built features do not transfer.** A logistic combination of gist, time,
  places, numbers and actors, trained on two sets and tested on the third, scored
  AUC 0.94–0.97 but lower recall at 95% precision than the gist alone on two of
  the three sets; gist + time + places + numbers alone fell to AUC 0.86–0.95.
- **No threshold is safe alone.** Precision of the gist alone at cosine ≥ 0.97 was
  0.94 on silver and batch 3; false merges persist at the top. At 95% precision it
  recovers only 49–67% of true duplicates. A judge breaks the trade-off.
- **No signal in photos or publishers.** Outlets shoot their own pictures; the
  same outlet files several different stories a day.

Two corrections came out of reading the disagreements: `gold_pairs` paired the
Thrissur leopard with a Palakkad one as "same" (two labels corrected, 61 → 59
positives; the gist scored them 0.89 — it would have merged two animals, Jev
said 0.05), and "BJP spends ₹287 crore in Bengal" vs "₹529 crore on five states"
— first read here as a templated false pair — is one ADR report (69% shared text).

### Within and across sources

- **Syndicated wire copy** (near-identical bodies across publishers, MinHash
  containment ≥ 0.6): 92 pairs in a week, 17 of them split across events. Small,
  and caught by the verified tier because their summaries are near-identical — no
  separate tier.
- **Same outlet, several articles on one happening** (NDTV's three Mushtaq Khan
  pieces): not a text-duplicate problem; they are different articles about the same
  death, which the verified tier judges like any other.
- **Same article in several edition feeds** (`thehindu`, `thehindu_kerala`):
  identical URL → `url_exact`; and extraction is paid once per URL
  (`enrichment/consumer._extraction_for_same_url`).

## The verified tier

`correlation/verify.py` + `correlation/clustering._match_by_gist_verified`.

```mermaid
sequenceDiagram
    participant E as enrichment
    participant C as correlation (under the match-or-create lock)
    participant DB as Postgres
    participant J as Jev (OpenRouter Decisions)
    E->>E: extract (English headline, summary, entities…)
    E->>E: embed chunks + gist ("headline. summary", query: prefix) in one call
    E->>DB: articles.gist_embedding
    C->>C: cve / url / title / headline / embedding / entity tiers refuse
    C->>DB: nearest member articles by gist within 0.10, in-window events, top 5
    DB-->>C: candidate events + distances
    C->>DB: each candidate's FOUNDING headline + summary + first seen
    C->>J: ARTICLE + EVENT_1..EVENT_k, one noul question per event (6 s ceiling)
    J-->>C: P(same happening) per event
    C->>DB: event_match_verdicts (every answer, with mode)
    alt live and max P >= 0.85
        C->>DB: attach (match_type = verified, score = P)
    else shadow, below floor, error, timeout
        C->>DB: found a new event (exactly as before the tier)
    end
```

Design decisions and why:

| Decision | Why |
|---|---|
| Last tier, only for articles every other tier refused | purely additive: it can only turn a would-be new event into an attachment; measured tiers are untouched |
| Candidates from **member articles**, not a per-event average | an average drifts toward whatever a wrong merge brought in and then draws more of it — the loop that once grew a Kannada event to 139 articles |
| Judged against the event's **founding** headline + summary | never moves, so no transitive chaining (the 46-event union-find group) |
| Gist floor cosine 0.90 (distance 0.10), mE5 only | every labelled September duplicate sat at ≥ 0.898 (silver) / ≥ 0.929 (batch 3); a candidate floor, not a merge threshold. Off on mpnet (unmeasured) |
| Attach at Jev ≥ 0.85 | precision 1.00, recall 0.75 on silver; 20/20 in a production sample. 0.7 gives recall 0.94 at precision 0.97 on silver — lower it only on labels |
| One call per article, all candidates in it | batched and pairwise scored the same (AUC 0.988 vs 0.987 on batch 3) |
| 6 s ceiling; any failure founds a new event | Jev runs under correlation's advisory lock; an outage must cost a missed merge, never a stalled pipeline |
| The question names the traps literally | Jev is literal: "different figures" (Mushtaq Khan's age was reported as 56, 67, 75 and 76), "another instance of a recurring kind" (co-ops, Lok Adalats) |

## Confirm mode: every fuzzy attach verified (0.0.118.0)

`PRISM_EVENT_VERIFY=confirm` (`correlation/clustering._verified`). The exact tiers
(`cve_id`, `url_exact`) still attach on their own. The title, headline, embedding and
entity tiers only **propose**: every tier runs, their events join the gist candidates,
and one Jev call asks, per candidate, *the same happening?* and *a later development of
it?* (`verify.SAME_STORY`).

| Jev's answer | What happens |
|---|---|
| same happening ≥ 0.85 | attach (`match_type` = the tier that proposed it, or `verified`) |
| a record a tier **proposed**: same happening ≥ `PRISM_PROPOSAL_VERIFY_MIN` (default 0.85, the gist floor) and later development below `PRISM_FOLLOW_UP_MIN` | attach under the proposing tier (0.0.120.0) |
| below that, later development ≥ `PRISM_FOLLOW_UP_MIN` (0.85) | the article founds its own record, and the earlier record `leads_to` it (`event_links.method = 'verified'`); the record page lists it under "Earlier and later" |
| neither | a new record |
| Jev failed, timed out, or there is no text to judge | a **title** proposal attaches as before (92%); an embedding or entity proposal (76%, 44%) does not — a new record is the cheaper mistake, and the record merge folds it later |

**Why.** Scored by Jev's own same-happening test on 781 production attaches
(2026-09-24..28): the verified tier 100%, title 92%, embedding 76%, **entity_overlap
44%** (28% clearly different). entity_overlap carried 19% of all attaches and 56% of the
records shown as covered by two or more outlets. Its errors were mostly follow-ups (the
parents' hunger strike attached to the student's death, 67 articles in one record) and
sometimes unrelated (one cricketer's milestone into another's century). Founder decision
1A (2026-09-29): **a record is one happening**; follow-ups are separate records linked
as later developments, until the story layer is verified.

**Two floors (0.0.120.0).** The first hour of confirm in production (2026-10-01) split
far more than the replay predicted: 77 of 335 new records had a candidate Jev scored
0.5–0.85, and one Flydubai cockpit attack had five records scoring 0.70–0.80 against
each other. A record a tier proposed has that tier's evidence behind it; in the 30-day
repair dry run, read by hand, the proposals Jev did *not* also call a later development
were the same happening 21/30 at 0.50–0.60, 24/30 at 0.60–0.70 and 25/30 at 0.70–0.85;
about 10 of 15 it did call one were later developments (bail granted → "family reacts to
bail"). Record-to-record pairs are worse below ~0.7 (reactions: "Trump praises the
pilot"), so the record merge keeps 0.85. A proposal attaches from
`PRISM_PROPOSAL_VERIFY_MIN` unless Jev's later-development answer reaches
`PRISM_FOLLOW_UP_MIN`, which founds a linked record; a record only the gist found keeps
0.85 (`clustering._attaches`). These are reads, not labels: the founders' attach check
(`/label`, batches `v_tQBu8kPmAc`/`vabpufxFYUjP`, stratified by band) sets the floor.

**The record as it stands (0.0.121.0).** The judge reads each candidate's founding headline
and summary, then up to two **confirmed** members' headlines nearest the incoming article's
gist ("Also reported as: …"; `verify.event_blocks(near=gist)`). Confirmed means an exact or
verified tier, or a verdict at the proposal floor — a member swept in by shared names before
confirm mode is never shown. On the 292 labelled attach pairs (model labeller, blind,
2026-10-01) at the 0.65 proposal floor: recall 0.727 → 0.770, precision 0.975 → 0.976.

**Floor set from labels (2026-10-01).** `PRISM_PROPOSAL_VERIFY_MIN=0.65` on the worker. The
`/label` attach batches (`v_tQBu8kPmAc`, `vabpufxFYUjP`, 300 pairs stratified by tier and
band) were labelled by the **model labeller** account (Claude Opus 5.5, founder instruction,
blind to the verifier's answers). With the later-development veto: 0.85 → P 1.000 R 0.466;
0.75 → P 0.972 R 0.640; **0.65 → P 0.975 R 0.727**; 0.50 → P 0.957 R 0.832. The old tiers on
their own, by the same labels: title 0.90, embedding 0.79, entity_overlap 0.48. Model labels
share blind spots with the verifier — a human pass on the same batches is the check on both.

**Replayed** (`tools/score_cascade --verify 0.85 --confirm --sets gold,batch3,silver`,
mE5, `query:` prefix, 785 labelled pairs, 2026-09-30):

| mode | true merges | false merges | missed | P | R | F1 |
|---|---|---|---|---|---|---|
| `live` | 84 | 5 | 78 | 0.944 | 0.519 | 0.669 |
| `confirm` | 80 | 2 | 82 | 0.976 | 0.494 | 0.656 |

Three of five wrong merges gone for four true ones: precision first, with no compounding
collapse (the headline gate on this path once cost 37% recall). The labelled sets are
mostly same-happening pairs; production's errors were mostly follow-ups, which the
human sheets (`tools/gold_attaches`) measure directly.

**The follow-up question**, measured on 60 attaches Jev judged not the same happening:
every pair at ≥ 0.85 read as a real follow-up (a Supreme Court ruling upholding a High
Court's, a player declared fit after the injury, the accused produced in court); below
0.5 they were different matters (another meeting, another semifinal).

**The backlog** (`tools/repair_attaches`): the same two questions for every fuzzy
membership in a window; a dry run writes a CSV and changes nothing; `--apply` moves the
ones under `--detach-below` through the live path (they join the record they do report,
or found their own, linked when Jev says so), at the time they first arrived, and
rebuilds what they left without moving it up the feed. Dry run, 7 days to 2026-09-28,
4,217 attaches:

| tier | same (≥ 0.85) | likely same (0.5–0.85) | likely different (0.15–0.5) | different (< 0.15) |
|---|---|---|---|---|
| title_time | 255 | 58 | 16 | 21 |
| embedding | 407 | 260 | 150 | 64 |
| entity_overlap | 677 | 669 | 889 | 751 |

At `--detach-below 0.5`, 1,891 would move, 452 of them linked as follow-ups.

**The human check** (`tools/gold_attaches`): Jev scored the old tiers and Jev replaced
them, so the numbers above are not independent. 300 article-vs-record pairs, stratified
by tier and band, blind, two labellers with 100 in common; `--score` gives agreement,
the verifier's precision and recall at 0.5 / 0.7 / 0.85, the follow-up links' precision,
and the old tiers' true share reweighted to the window.

## Cost and latency

| | Measured |
|---|---|
| Jev per pair (event blocks) | $0.0000225 (17,590 pairs, $0.39, 2026-09-25) |
| Jev per pair (article blocks) | ~$0.000048 (1,602 calls, $0.077) |
| Latency | ~250 ms per call |
| Candidate pairs per day | ~2,500; ~830 articles a day have a candidate |
| **Monthly** | **≈ $2–4** at current volume |
| Gist embedding | one extra ~40-token embedding per article, in the same fastembed call |

For scale, extraction is the dominant spend (`docs/ML-EVALUATION.md`).

## Rollout

1. **Deploy with `PRISM_EVENT_VERIFY=off`.** Migration `e5a9c3b7d2f1` adds the
   column, `ix_events_last_updated` and `event_match_verdicts`.
2. **Backfill gists** for the window: `DATABASE_URL=<prod> uv run python -m tools.backfill_gist --days 14 --apply`
   (no LLM spend).
3. **Replay** the cascade with the tier on (`tools.score_cascade --verify 0.85 --sets gold,batch3,silver`)
   — ship only if it beats the current cascade. **Done 2026-09-25: F1 0.302 → 0.685,
   precision 0.909 → 0.947** (table above).
4. **Shadow for ≥ 3 days** (`PRISM_EVENT_VERIFY=shadow` on the worker): every
   would-be attachment is recorded (`event_match_verdicts.mode = 'shadow'`,
   log line `event_verify_shadow`). A founder reads 50 sampled would-be merges.
5. **Live** — since 2026-09-27 17:12 UTC. Watch: share of articles founding new events
   (baseline ~75%), single-article events (85%), the weekly copy rate
   (`tools/audit_event_dups`, 10.1% at 0.85 on 09-25, **1.4% on 2026-09-29** after the
   09-27 record merge), `event_verify_failed` rate, correlation lock time.
6. **Confirm** (0.0.118.0): `PRISM_EVENT_VERIFY=confirm`, then `tools/repair_attaches`
   (dry run, founder review, `--apply --limit 50` canary, the rest), then the labels
   (`tools/gold_attaches`). Back to `live` restores the old tiers exactly.

## Datasets

| Set | Where | Pairs (same) | Labelled by | Status |
|---|---|---|---|---|
| gold_pairs, July | `tools/gold_pairs.py` | 398 (59) | founders, 2 batches | ratified; 2 labels corrected 2026-09-25 |
| batch 3, cross-language | `tools/gold_same_happening.BATCH_3_CROSSLINGUAL` | 268 (43) | two labellers, batch `MGDmtLPZOdjy` | 40 disputed pairs excluded; some "no"s are granularity calls |
| silver, same-language | `tools/gold_same_happening.SILVER_SAME_LANGUAGE` | 128 (64) | Claude, from headline + summary | **unratified** — to be replaced by a labeller batch |

## How to measure

```bash
# The copy rate on production, judged the way the tier decides (read-only; --judge spends ~$0.40/week, cached)
uv run python -m tools.audit_event_dups --judge --days 7 --tau 0.7 0.85

# Replay the whole cascade on the labelled sets, with and without the tier (local scratch schema; Jev cached)
uv run python -m tools.score_cascade --models intfloat/multilingual-e5-base --doc-prefix query \
    --sets gold,batch3,silver --verify 0.85

# Compile a finished label batch into pairs
uv run python -m tools.gold_crosslingual --compile <KEY>

# Confirm mode, replayed: the fuzzy tiers only propose
uv run python -m tools.score_cascade --models intfloat/multilingual-e5-base --doc-prefix query \
    --sets gold,batch3,silver --verify 0.85 --confirm

# Re-judge the fuzzy tiers' attaches (dry run: a CSV, nothing moved), then the human check
DATABASE_URL=<prod> uv run python -m tools.repair_attaches --days 7
uv run python -m tools.gold_attaches --sample 300 --days 7
uv run python -m tools.gold_attaches --score A.csv B.csv --key .context/label_attaches_<ts>.key.json
```

Rules that have held in this code (see the comments in `correlation/clustering.py`):
a pairwise number is not a cascade number — replay before flipping a tier;
thresholds move with the embedding model; calibrate Jev floors on labels, not 0.5.

## Open work

- **Repair the backlog** — built, `correlation/merge.py` + `tools/merge_duplicates.py`
  (founder decision 2026-09-27: merge now). Input: shadow verdicts >= 0.85 whose
  article founded its own record. The copy folds into the record Jev named, resolved
  to a survivor that is not itself a copy (star, never a chain); a copy holding any
  article nobody judged the same happening is reported, not merged. Members and every
  table that points at events move (`merge.HANDLED_TABLES`, checked against the schema
  by a test; paid `lens_unlocks` included), the survivor's projection is rebuilt in the
  same transaction, `events.merged_into` is set, and `/api/v1/events/<copy>` answers
  308 → the survivor (the story page turns it into a permanent redirect). Dry run
  2026-09-27 on production: 591 merges into 409 survivors (108 through a copy, chains
  up to 4 deep), 158 skipped (175 entity_overlap, 73 embedding, 45 title_time members
  never judged). Dry run by default; `--apply --limit 20` first.
- **Duplicate records built from several articles** — `tools/merge_duplicates --events`
  (`merge.plan_events`). The shadow verdicts cannot reach them, so the records are
  judged record to record: every served record of the last `--days` (7) is paired
  with its five nearest by the FOUNDERS' gists (cosine >= 0.90, first seen within
  72h), and Jev judges the two founding headlines + summaries, batched as the live
  tier batches. Groups are stars (`merge.stars`): survivor = most publishers, then
  earliest; a record joins only on its own verdict against the survivor (>= 0.85);
  a record reached only through another is judged against the survivor directly
  (one extra call) or left out. It moves whole. Answers already on file in any mode
  are reused; `--apply` keeps this run's as `event_match_verdicts.mode = 'pair'`
  (article = one record's founder, event = the other). Dry run 2026-09-27 on
  production: 14,664 records, 21,255 gist pairs (6,464 answered before), 14,865
  pairs judged in 6,042 calls for $0.22; 1,045 merges into 664 survivors (the
  Parvesh Verma slap 6 → 1, a Yamuna Expressway bus fire 23 → 1). The 0.85–0.87
  band (161 merges) holds the doubtful ones: a follow-up ("CCTV footage reveals…")
  and a repeat daily RBI auction 57h apart, both at exactly 0.850 — tighten a run
  with `PRISM_EVENT_VERIFY_MIN=0.87`.
- **Ratify silver**: push it as an `event_identity` label batch for two labellers.
- **The title tier compares unlike things** (outlet title vs Prism headline) — test
  outlet-title-vs-founder-title in replay, or retire it if the verified tier
  subsumes it.
- **Site furniture in `clean_text`** hurts the body embedding and Ask/RAG, not
  this tier. Per-publisher furniture stripping is its own ticket.
- **Wikidata QIDs** would give identity-level matching, but only 1.8% of entities
  carry one today.

## References

- Miranda et al., *Multilingual Clustering of Streaming News*, EMNLP 2018 — documents compared against a cluster's aggregate of all members, English as the pivot language. <https://aclanthology.org/D18-1483/>
- Nakshatri et al., *Using LLM for Improving Key Event Discovery: Temporal-Guided News Stream Clustering with Event Summaries*, EMNLP 2023 Findings — assign articles by embedding LLM-written event summaries; LLM pair check to merge clusters. <https://aclanthology.org/2023.findings-emnlp.274/>
- Chen et al., *SemEval-2022 Task 8: Multilingual News Article Similarity*. <https://aclanthology.org/2022.semeval-1.155/>
- Near-duplicate detection for wire copy (MinHash vs SimHash). <https://medium.com/@jonathankoren/near-duplicate-detection-b6694e807f7a>
