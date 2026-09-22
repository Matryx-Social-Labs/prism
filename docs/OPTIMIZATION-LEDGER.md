# Optimization ledger

Every change made in the 2026-09 hardening programme, with the number before and
the number after, and how each was measured. A row without a measurement is not
an optimization, it is a hope — it does not go here until it is measured.

Conventions: cost is USD per item at OpenRouter list price on the day; latency is
wall time from the worker's point of view; agreement figures name the sample.

## Model calls

| # | Change | Before | After | Measured how | Date |
|---|---|---|---|---|---|
| 1 | Relevance gate + classifier → one typed Jev call (`classification/decide.py`, `PRISM_DECISIONS_MODE=live`) | 2 chat calls on gemini-3.1-flash-lite, ≈ 2,500 in + ≈ 140 out tokens, **≈ $0.0008/item**, 2–6 s; JSON parse failures retried at full price; Gemini PROHIBITED_CONTENT refusals on crime reports routed to the fallback model | 1 call on typesafe/jev-1.13, ≈ 2.5k in tokens, **≈ $0.00013/item**, 0.32–0.6 s; no parse path, no content refusals | `tools/bakeoff_decide` 450 prod items (`.cache/bakeoff_decide.json`, `usage.cost` summed); smoke timings 2026-09-22 | 2026-09-22 |
| 2 | Same — accuracy | LLM pair (the silver standard) | gate agreement en 77 % / hi 89 % / kn 85 %; sector 90 / 90 / 83 %; route 98 / 93 / 95 %; language 100 / 99 / 99 %. Gold: relevance 27/27, sector 31/32, subsector 12/13. Disagreements on `business` and `markets` read by hand: the LLM was wrong (school shooting → business; ₹51-lakh co-op profit → market-moving) | bake-off per language; `evals/datasets/*.jsonl` through `to_results` | 2026-09-22 |
| 3 | Noul crossing points set from data, not 0.5 (`EVENT_MIN` 0.3, `NOT_NEWS_MAX` 0.4, `FAST_LANE_MIN` 0.7, `cyber` 0.7) | route agreement 65–80 % at 0.5; fast-lane false positives 23 % | route 93–98 %; fast-lane recall 4/4 prod, 6/6 gold at 4 % false positives | `tools/bakeoff_decide --from-cache` re-scoring the same raw answers | 2026-09-22 |
| 4 | Clip judge → Jev choice (`PRISM_JUDGE_BACKEND=decide`) | gemini-3.5-flash one-word verdict: event-precision 1.00, recall 0.56, 3-way accuracy 0.71 on the 24 gold pairs it had cached | precision 1.00, recall 0.75, accuracy 0.88 on all 42 gold pairs still in prod; ≈ $0.00002/pair | `tools/gold_clips.jsonl` vs `clip_verdicts` (LLM) and a live Jev pass | 2026-09-22 |
| 5 | Story veto → Jev noul | flash-lite: keep-recall 0.98, separation 0.79 (162-pair subsample) | keep 0.86, separation 0.87 on the same 162; 0.88 / 0.89 on all 1,147 ratified pairs. A trade (LLM keeps more, Jev separates more); founder chose separation | `tools/gold_story_pairs.pairs()` grounding rebuilt from prod events | 2026-09-22 |

## Pipeline code

| # | Change | Before | After | Measured how | Date |
|---|---|---|---|---|---|
| 6 | `podcasts/judge.py` + `xposts/judge.py` → `common/pair_judge.py` | two ~90 %-identical functions (107 + 93 lines); pairs judged **one at a time**, one INSERT per pair, DB session held across the loop; a failed verdict raised `TypeError` in the except (structlog `event=` collision) and killed the run | one function (143 lines incl. both backends); 4 pairs in flight (`JUDGE_CONCURRENCY`), verdicts in one `executemany`; a failed pair logs and is skipped | `tests/test_pair_judge.py` asserts peak in-flight > 1 and exactly one INSERT batch; mutation-verified | 2026-09-22 |
| 7 | Classification write → one conditional `UPDATE … WHERE relevance='pending'` | second `session_scope`: SELECT the row again, mutate, ORM flush (2 round trips); a second worker holding the same item across the model call could overwrite a settled row | 1 round trip; rowcount decides publish; the settled row wins | `tests/test_classification_consumer.py::test_an_item_settled_by_another_worker_mid_call_is_not_overwritten` | 2026-09-22 |

| 8 | `structured_chat` under one deadline; SDK retries 2 → 1 (`common/llm.py`) | worst case per hung call: 3 SDK attempts × 3 parse retries × fallback × 90 s ≈ 13.5 min holding an enrichment slot | ≤ 180 s, then redelivery | `tests/test_hardening_security.py::test_a_hung_provider_costs_one_deadline_not_nine_attempts` | 2026-09-22 |
| 9 | Per-model 429 cooldown (`common/llm.py`) | any model's 429 paused every stage incl. the user-facing Ask stream for 120–900 s | only that model pauses; 401/402/403 stay global | `…::test_a_429_pauses_only_the_model_that_hit_it` | 2026-09-22 |
| 10 | Thread-link verdict writes → `executemany` (`correlation/threads.py`) | up to 15 sequential INSERTs per event (~600 linked events/day ≈ 9k round trips) | 1 round trip per event | code; DB round trips counted | 2026-09-22 |
| 11 | Embedding shadow gate removed | one fastembed call per gated news item (~2,500/day) logging a score nobody consumed | 0 | code; the 2026-07-20 calibration verdict recorded in CHANGELOG 0.0.86.0 | 2026-09-22 |

## Pending (measured at the time each lands)

Source cache per item; DF-CTE precompute in
`_story_component`; duplicate-URL re-embed; thread-link and ask-guard hybrids
on Jev; web bundle and Lighthouse; SEO levers. See `.claude/plans/product-hardening.plan.md`.
