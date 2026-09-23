# Plan: the cross-language merge hole

**Source**: founder report — two UNGA stories, one English, one Kannada, not corroborated
**Complexity**: Medium (the switch exists; the evidence to flip it does not)
**Depends on**: `quote-language.plan.md` must ship FIRST — see Sequencing

## The reported pair, gate by gate

`7f9d86ff` — 2 English articles (Hindustan Times 14:53, LiveMint 17:37),
"Trump Reiterates He Ended India-Pakistan War at UNGA".
`515fd078` — 2 Kannada articles (TV9 Kannada 17:14, 17:32), same claim.
Same day, 6 shared entities, event-embedding cosine distance **0.1146**.

`find_event` (`correlation/clustering.py:190`) ran every tier and each one was
structurally unable to see the match:

| tier | outcome |
|---|---|
| `cve_id` | n/a |
| `url_exact` | different URLs |
| `title_time` (trigram ≥ 0.6) | compares the **native** Kannada title against an English event title — ~0 by construction |
| `headline_xlang` | **OFF in production** (`prism_headline_tier_threshold = 0.0`, no override) |
| `embedding` (≤ 0.050) | **skipped**: `detect_script` = kannada, not in `EMBEDDING_TRUSTED_SCRIPTS`. Correct — the Kannada subspace is collapsed (AUC ≈ 0.5) |
| `entity_overlap` | the only path left, and it failed **twice over** |

The entity tier failed on the outer guard first: `ENTITY_MATCH_LOOSE_DISTANCE` is
**0.106** for `multilingual-e5-base` and the distance is **0.1146**, so the English
event is filtered out by the `WHERE` before the `HAVING` is ever evaluated — missed
by 0.0086.

And it would have failed anyway. Shared actors, with their in-window df:

| actor | type | df | 1/df | counts? |
|---|---|---|---|---|
| Shehbaz Sharif | person | 15 | 0.067 | yes |
| United Nations General Assembly | organization | 56 | 0.018 | yes |
| Donald Trump | person | 272 | 0.004 | yes |
| Pakistan | government | 104 | 0.010 | **excluded type** |
| United States | place | 282 | 0.004 | **excluded type** |
| India | government | 489 | 0.002 | **excluded type** |

`sum(1/df) = 0.089` against `ENTITY_MATCH_MIN_IDF = 0.15`; top IDF 0.067 against
`ENTITY_MATCH_MIN_TOP_IDF = 0.1`; 3 shared actors against `ENTITY_MATCH_BROAD_SHARED = 4`.

**So this is not a threshold that is 0.0086 too tight.** The entity tier is built on
the premise that a *specific* actor carries the match (Delhi Metro at df 6). An
international story has no specific actor — every participant is a national magnet,
and the three most specific ones are typed `government`/`place` and excluded outright.

`tools/gold_crosslingual.py` says this in its own docstring, dated **2026-09-17**:

> "The cross-language path in `correlation/clustering.find_event` is the entity tier,
> which needs two shared person/company/organisation actors — so a story whose actors
> are countries, courts and governments cannot bridge at all."

The hole was found five days ago, the fix was built behind a switch, and the labels
that set the switch's threshold were never gathered. Nothing is failing silently.

## Is it happening a lot? Yes

Distance is useless as a prevalence measure here — mE5's *different*-event median is
0.145, so "within 0.25" is nearly every pair in a 4-day window (38.7M of them). The
anchor is `gold_crosslingual`'s measured band: ≥0.55 on the two extracted English
headlines was the same happening every time it was read.

Cross-language event pairs (no article language in common), 4-day window, 16,469 events:

| headline cosine | pairs | events touched |
|---|---|---|
| **≥ 0.55** (read as the same happening every time) | **621** | **915 (5.6% of all events)** |
| 0.39–0.55 (about half were) | 1,244 | 1,701 |

By language pair at ≥0.55: en+hi 237, en+kn 206, hi+kn 89, en+hi+kn 25, en+ta 8,
kn+ta 6, en+gu 5, hi+ta 4.

**The top of that band is byte-identical.** Twelve of the highest-scoring pairs are
the same Prism headline written twice:

```
['pa'] Delhi High Court grants bail to Jagtar Singh Johal
['en'] Delhi High Court grants bail to Jagtar Singh Johal
['hi'] Sikh truck driver stabbed 17 times in Wyoming
['en'] Sikh truck driver stabbed 17 times in Wyoming
['ta'] Elavenil Valarivan wins two silver medals at Asian Games
['gu'] Elavenil Valarivan Wins Two Silver Medals at Asian Games
```

About one event in eighteen has an unmerged cross-language twin in the certain band.
Every one is a split record: the corroboration count is wrong, the coverage bar is
wrong, and a reader is shown two half-stories instead of one.

## Sequencing — the quote fix must land first

Today only **41 events** carry claims in more than one language, because cross-language
coverage mostly fails to merge. Fixing the merge does not create the quote-language
problem — it **multiplies it**, by roughly an order of magnitude, the day it ships.
Merging first would take a card that occasionally prints a translation as verbatim and
make it the normal case.

So: `quote-language.plan.md` Phase 0 ships **before** the headline tier is flipped on.

## Phases

### Phase 1 — flip the tier on at the certain band, on cascade-replay evidence

`_match_by_headline` already exists and already does the right comparison: the
extractor's **English** headline for the incoming article against events' Prism
English headlines, IDF word-cosine, 4-day window. Only the threshold is missing.

- Do **not** ship at 0.39. The 0.39–0.55 band is where `gold_crosslingual` read about
  half as wrong, and this file's own history is four separate occasions where a
  pairwise number over-promised and the cascade contradicted it.
- Ship at **≥0.55** first — 621 pairs, topped by identical headlines.
- **Replay before flipping**: `uv run python -m tools.score_cascade` against
  `gold_pairs`, per this file's standing rule ("flip it only on cascade-replay
  evidence, never on a pairwise number"). The risk to measure is compounding, which
  pairwise scoring cannot see.
- Note the tier's blind spot: it requires `e.headline_by = 'prism'`, so an event still
  carrying the first report's own headline is invisible to it. Measure how many.

### Phase 2 — gather the labels for the ambiguous band

`tools/gold_crosslingual.py --propose / --push / --compile` is built and unused. Run
it. The 1,244 pairs at 0.39–0.55 are exactly its candidate net. Only then consider
lowering the threshold.

### Phase 3 — a signal that does not break on tokenisation

The reported pair scores **0.331** — below even 0.39 — although it is plainly the same
happening. The cause is the word tokeniser, not a missing signal: `UN` vs `UNGA`, and
`India-Pakistan` as one token against `India` + `Pakistan` as two.

Every article, in every language, already carries an extractor-written **English**
headline and English summary. Embedding *those* moves the comparison into the Latin
subspace, where the model is healthy, and turns a cross-language match into a
same-language one — no new model call, only a local fastembed pass.

Measure against the same gold set before adopting; it replaces the word-cosine inside
the same tier, so it is a swap, not a new path.

### Phase 4 — the 621 pairs already on disk

The tier only runs at ingest, so it cannot repair history. Merging two existing events
moves `event_memberships`, rebuilds projections and disturbs the story layer, so this
is a tool with a dry run and a founder-reviewed sample, not a migration. Scope it after
Phase 1 has proven the threshold on live traffic.

## Not findings

- ~40 entities out of 58,905 carry malformed `entity_type` values (`org  anization`,
  `government|subject`). Real but immaterial — 81.5% of entities are matchable and the
  excluded types are excluded by design.

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| A false merge compounds — the merged event becomes a wronger candidate for the next article | Medium | ship at 0.55 not 0.39; cascade replay first; this repo has the 139-article incident on record |
| Merging multiplies mixed-language quote cards ~10x | Certain | quote-language Phase 0 ships first — see Sequencing |
| Phase 4 damages the story layer | Medium | dry run + founder-reviewed sample; not a migration |

## Acceptance

- [ ] `tools/score_cascade` replay recorded for the chosen threshold, not a pairwise number
- [ ] Two events with the same Prism headline in a 4-day window cannot both exist
- [ ] Mixed-language quote cards are honest before the merge rate rises

## Outcome (2026-09-23)

- **Phase 1 (flip the tier) is BLOCKED on labels, not on code.** The replay
  harness could not see the tier at all (fixed: it now copies `headline_by` and
  titles events as the consumer does). But `gold_pairs` holds July articles and
  extracted English headlines only exist from 2026-09-16, so the tier cannot
  fire on any existing labelled pair. Baseline on the corrected harness, mE5,
  tier off: P 0.8857 R 0.5082 Cdet 0.5393 (held out P 1.0000 R 0.4848).
- **Phase 2 is in the founders' hands**: batch `tKECdZfjiL0n` (150 tasks, 364
  candidate pairs). Invite with `tools/gold_candidates --invite Name Name
  --batch tKECdZfjiL0n`; compile with `tools/gold_crosslingual --compile`;
  then `tools/score_cascade --headline-tier 0.55` on the compiled set.
- **Phase 3**: `tools/score_headline_signal` built. Reported UNGA pair: word
  cosine 0.329, mE5 headline embedding 0.932. Scores the batch once answered.
- **Phase 4 NOT BUILT.** ~15 tables reference an event id, including
  `lens_unlocks` (paid, no cascade); a merged-away `/story/<id>` is indexed and
  shared and needs a redirect. Which id survives is a founder decision.
