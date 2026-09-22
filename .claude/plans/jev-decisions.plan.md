# Plan: Typed decisions on TypeSafe Jev (OpenRouter) for the classification stages

**Source**: conversational (`/ecc:plan`, 2026-09-22)
**Complexity**: Medium (Phases 0–2), Small (3–4), decisions pending (5)

## Summary

Move the decision-shaped LLM stages (relevance gate, classifier, clip/x-post judges, story veto)
to `typesafe/jev-1.13` via OpenRouter `POST /api/alpha/decisions`, one typed call per item, behind
a shadow → live flag, gated by a per-language agreement bake-off against the 20k LLM-labelled
prod items. Extraction, event-analysis, briefs, Ask stay on LLMs — Jev cannot emit text.

## What Jev is (verified 2026-09-22)

- TypeSafe AI "System One" model, released 2026-09-15. Returns typed answers + probabilities,
  no text. Three question types: `noul` (yes/no probability), `choice` (≤255 options, returns
  `choice`, `confidence`, `probabilities`), `score` (2–10 ordered levels).
- OpenRouter: `POST https://openrouter.ai/api/alpha/decisions`, Bearer `OPENROUTER_API_KEY`
  (same key as today — smoke-tested, works). Body `{model, state: {...}, questions: {key: {type,
  instructions, criteria}}}`; response `{answers, usage: {input_tokens, output_tokens, cost}, id,
  provider}`. Noul answer is `{"noul": 0.93}` (probability, not bool). NOT the chat API — a model
  swap in `structured_chat` will not work.
- $0.042/M input, output free. 64k combined context, 32k per question. 1,200 rpm / 250k tok/s.
  Alpha endpoint; `jev-latest` changes without notice → pin `jev-1.13`.
- Documented limits: literal reading (negations/scoping land at face value), no arithmetic,
  dates are text, no generation, accuracy falls with irrelevant state, and "text engineered to
  argue for its own classification can move the answer". Multilingual support: undocumented.
- Smoke test (4 items, en/kn/hi): all correct incl. Kannada court story → relevant 0.89,
  politics, IN-KA, `kn`; Hindi listicle → relevant 0.02. 320–600 ms. $0.000044–0.000049 per
  item for gate + classify + state + language + 3 nouls in ONE call.

## Where Prism decides with an LLM today

| Stage | Call site | Output shape | Model | Volume (prod, 7d) | Jev fit |
|---|---|---|---|---|---|
| relevance-gate | `classification/consumer.py:125` | bool + reason(audit) | flash-lite | 1,400–2,800/day | noul — yes |
| classifier | `classification/consumer.py:141` | sector(10), subsector(36), regions(list), language, role_interests(2), route(2), confidence | flash-lite | 1,000–2,300/day | choices + nouls — yes; regions → see below |
| clip-judge / tiebreak | `podcasts/judge.py:83,146` | `about` ∈ {event,topic,unrelated}; pick ⊆ menu | gemini-3.5-flash | per pair | choice / nouls — perfect fit |
| xpost-judge | `xposts/judge.py:69` | same | judge | not live | same |
| story-veto | `correlation/partition.py:780` | same_story bool + conf + reason | gate model | per member on partition runs | noul — yes (staged, not serving) |
| thread-link | `correlation/threads.py:66` | per candidate related/direction(3)/**rationale**/conf | glm-5.3-flash | ~600 linked/day | related+direction yes; rationale is user-facing (`StoryTimeline.tsx:13`) → hybrid only |
| ask-guard | `common/moderation.py:53` | allowed + category(5) | flash-lite | per Ask | adversarial boundary → hybrid only (security verdict) |
| extraction / event-analysis / briefs / digest / Ask | enrichment, correlation, agent | prose + nested records | various | 45% + 24.5% of spend | **no** |

**Regions**: extraction already owns country codes — `correlation/consumer.py:146` prefers
`shared.regions`; the classifier's regions only contribute IN-state codes (`:157`) and a fallback.
Prod 30d: 96% of country mentions are in the top 20; 29 states, IN-KA dominant. So the Jev
classifier asks `indian_state` (36 codes + national + none) and `primary_country` (top-20 + other),
and `regions = [primary_country, state]` — the contract is preserved without a free-form list.

**Language**: prod 30d = en 48%, **kn 31%**, hi 18%, then ta/ur/gu/bn/mr/te/pa. Kannada is the
acceptance gate.

## Cost / latency — honest numbers

Today gate + classify = 2 flash-lite calls ($0.25/$1.50 per M): ~2,500 in + ~140 out ≈
**$0.0008/item**, 2–6 s. Jev: **$0.000047/item**, ~0.4 s, one call. ≈ 17x per item; at ~2,500
gate items/day that is ≈ $2/day → $0.12/day, **≈ $55/month at today's volume** (scales with
sources). The larger wins are structural: two calls become one, no JSON parse failures or
retries, no Gemini content-policy refusals on crime reports (the fallback machinery is
unnecessary here), calibrated probabilities (a tunable gate threshold), ~10x latency. Extraction
stays the dominant cost and Jev cannot touch it.

## Patterns to mirror

| Category | Source | Pattern |
|---|---|---|
| Shadow rollout | `classification/consumer.py:66,103` + `common/config.py:187` | `prism_gate_mode == "shadow"` runs a scorer beside the LLM and logs `shadow_gate`; behaviour-neutral |
| Quota errors | `common/llm.py:42-56,89-100` | `LlmQuotaError(ConnectionError)` → stream redelivers; module cooldown on 401/402/403/429 |
| Tracing | `common/observability.py:observe` | lazy `@observe`, no SDK touched when `langfuse_enabled` is off |
| Settings | `common/config.py:39-82` | `prism_model_*` env-overridable, decision recorded in the comment |
| Concurrency | `correlation/partition.py:768-790` | `asyncio.Semaphore(VETO_CONCURRENCY)` + `gather` |
| Bake-off tool | `tools/bakeoff_extract.py`, `tools/bakeoff_brief.py` | pull N prod rows, run each backend, print a table |
| Evals | `evals/run_all.py` | Langfuse dataset task + evaluator per stage |
| Tests | `tests/test_llm_quota.py`, `tests/test_classification_regions.py` | pytest, stub the client, mutation-verified |
| Self-check | `classification/shadow_gate.py:demo` | `demo()` assert block |

## Phases

### Phase 0 — consolidate what the refactor would otherwise touch twice (from the code review)
1. Merge `podcasts/judge.py:judge_pairs` and `xposts/judge.py:judge_pairs` (~90% identical) into
   one parameterised `common/pair_judge.py` (cache table, id columns, fetchers, prompt); add
   `gather` + semaphore and one batched `executemany` INSERT (perf #3/#4). One Jev call site later
   instead of two.
2. `classification/consumer.py`: extract `_apply_feed_state()` and `_body_for_prompt()`; replace the
   three post-call mutations (`:82,161,163`) with `model_copy(update=...)`; second session → one
   conditional `UPDATE ... WHERE relevance='pending'` (perf #6).
- **Validate**: `uv run pytest -q tests/test_classification_regions.py tests/test_content_gate.py`
  + podcast gold rematch unchanged.

### Phase 1 — `common/decisions.py`: the Jev client
- `Noul/Choice/Score` request models, `NoulAnswer/ChoiceAnswer/ScoreAnswer`, and
  `async decide(state, questions, *, trace_name, metadata) -> dict[str, Answer]` over an
  `httpx.AsyncClient` singleton (httpx already a dependency), 15 s timeout, 2 retries on 5xx,
  same `HTTP-Referer`/`X-Title` headers. 402/429 → raise `LlmQuotaError` and share the existing
  cooldown (credits are account-wide); 4xx otherwise → `ValueError` (dead-letter once).
- Settings: `prism_model_decide = "typesafe/jev-1.13"` (pinned), `prism_decisions_mode:
  off|shadow|live` (default `off`), `prism_decisions_min_confidence` (default 0.0; set from shadow).
- Tracing: `@observe(as_type="generation")` + `update_current_generation(model, usage_details,
  cost_details={"total": usage.cost})`; log `decision` line with cost and latency either way.
- **Test** `tests/test_decisions.py`: request serialisation, response parsing, 402 → quota error,
  via `httpx.MockTransport`. No network.

### Phase 2 — gate + classifier on one Jev call, shadow first
- `classification/decide.py`: the question set (`is_relevant` noul; `sector` choice; `subsector`
  flat 36-way choice keyed `sector/sub` + none, validated by `valid_subsector`; `indian_state`
  choice from `common/regions`; `primary_country` choice; `language` choice; `cyber`, `markets`,
  `fast_lane`, `foreign_involved` nouls) and `to_results(answers) -> (GateResult,
  ClassificationResult)`. Instructions live in code (typed specs, not chat prompts) with a
  `questions_version` hash in metadata — Langfuse prompt management does not apply.
- `classification/consumer.py`: `shadow` → run `decide` beside the LLM pair, log
  `decision_shadow` with both verdicts and agreement per field (mirror `_log_shadow_gate`,
  never affects the outcome); `live` → Jev replaces both calls; any answer below
  `prism_decisions_min_confidence` falls back to the LLM path for that item.
- `tools/bakeoff_decide.py` (~60 lines, mirrors bakeoff_extract): replay N labelled prod
  `raw_items` (stratified by `language`), report gate/sector/subsector/state/route agreement per
  language and per sector, plus the confusion pairs. **Acceptance to flip live**: gate agreement
  ≥ LLM–LLM self-agreement on a re-run (measure it), sector ≥ 0.9 on en AND kn AND hi, no
  systematic bias on the cybersecurity over-tag the classifier prompt fights.
- `evals/run_all.py`: `--backend decide` variants of `relevance_task`/`classification_task` so the
  27 + 32 gold items score both.
- **Tests** `tests/test_classification_decide.py`: answers → results mapping (state/country
  regions, subsector validation, fast_lane/role_interests thresholds); shadow never changes the
  outcome; live with low confidence falls back. Mutation-verified.
- Rollout: `shadow` on prod for ≥3 days → bake-off → `live` → watch `rejected` ratio and
  sector mix daily vs the prior week; `off` is a one-env rollback.

### Phase 3 — judges on Jev (after Phase 0)
`clip-judge` → `about` choice; `tiebreak` → one noul per story. Gate on the podcast gold labels
(≥ current ~0.8 precision). `xpost-judge` inherits via the shared function.

### Phase 4 — story-veto on Jev
`same_story` noul with the existing grounding as state; score with `tools/score_stories` against
`tools/gold_story_pairs`. Fail-open semantics unchanged.

### Phase 5 — decisions, not in scope until 0–4 land
- thread-link: Jev for related/direction, LLM only writes rationale for accepted links (~600/day)
  — or leave as is (9% of spend).
- ask-guard: Jev `allowed` ≥ 0.9 → skip LLM, else today's LLM guard (security verdict: never
  Jev alone on an adversarial boundary). Prerequisite: mitigate the RAG system-prompt injection
  surface (security #1) first.

## Files to change

| File | Action | Why |
|---|---|---|
| `common/decisions.py` | CREATE | Jev client + question/answer models |
| `common/config.py` | UPDATE | `prism_model_decide`, `prism_decisions_mode`, `prism_decisions_min_confidence` |
| `classification/decide.py` | CREATE | question set + answers → results |
| `classification/consumer.py` | UPDATE | shadow/live wiring; Phase 0 extractions |
| `common/pair_judge.py` | CREATE | merged judge_pairs (Phase 0), Jev backend (Phase 3) |
| `podcasts/judge.py`, `xposts/judge.py` | UPDATE | thin wrappers over pair_judge |
| `correlation/partition.py` | UPDATE | veto on `decide` (Phase 4) |
| `tools/bakeoff_decide.py` | CREATE | per-language agreement bake-off |
| `evals/run_all.py` | UPDATE | `--backend decide` |
| `tests/test_decisions.py`, `tests/test_classification_decide.py` | CREATE | |
| `CHANGELOG.md`, `VERSION` | UPDATE | per repo convention |

## Validation

```bash
uv run pytest -q
uv run python tools/bakeoff_decide.py --n 600 --by language   # LLM_PROVIDER=openrouter
uv run python evals/run_all.py relevance --backend decide
uv run python evals/run_all.py classification --backend decide
graphify update .
```

## Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Kannada/Hindi accuracy below the LLM (31% + 18% of corpus) | Medium — 4/4 smoke OK, n=4 | Bake-off stratified by language is the gate; `off` rollback |
| Alpha endpoint changes shape or disappears | Medium | Pin `jev-1.13`; LLM path stays as the `off`/fallback mode |
| Literal reading breaks the gate's nuanced exclusions (opinion columns, gossip) | Medium | Phrase nouls positively; use 6k rejected + 20k relevant prod labels as silver set; threshold from shadow |
| Article text steers classification (injection) | Low, same class as today | Deterministic CVE/feed paths already bypass; no new surface |
| Prepaid credits exhausted → 402 | Low | Existing quota cooldown + stream redelivery |
| No prompt versioning in Langfuse for question specs | Certain | Specs in git; `questions_version` hash on every trace |
| Global cooldown couples Jev outages to LLM stages (perf #2) | Low | Only 402 shares the breaker; 429/5xx on Jev pause Jev alone |

## Acceptance
- [ ] Phase 0 lands with tests green and podcast gold unchanged
- [ ] `decide()` unit-tested without network; traces carry cost
- [ ] Shadow ≥3 days, bake-off table reviewed per language, threshold chosen
- [ ] Live on gate+classify; daily `rejected` ratio and sector mix within the prior week's band
- [ ] Judges and veto migrated with their gold sets unchanged or better
