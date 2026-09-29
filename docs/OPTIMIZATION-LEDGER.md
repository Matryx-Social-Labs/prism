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
| 12 | Extraction prefix marked for the cache: prompt + schema sent as ONE system message with `cache_control` (`common/llm._cached_prefix`, Gemini and Anthropic only) | Gemini's implicit cache served ~2,450 of the 4,380 fixed tokens, whatever the traffic (every call a hit; 4 of 12 cold after a 5.5-min gap); **$0.00069/call** on 20 articles; ledger average $0.00089 | all 4,380 read from cache on 20 of 20 calls, and on 6 of 6 through production `structured_chat`; **$0.00046/call** on the same 20 | the same 20 production articles through `structured_chat` in 3 variants (two system messages, merged unmarked, merged marked), `usage.cost` summed; json_object mode instead cached 0 and cost more | 2026-09-29 |
| 13 | Event analysis at minimal reasoning, pinned to Together (`correlation/consumer.py`) | glm-5.3-flash default reasoning, unpinned: 2,567 output tokens, **39.5 s median, $0.00166/call**; the ledger's second-largest line | 661 output tokens, **9.2 s, $0.00053/call**, 8/8 valid, briefs as grounded when read side by side | 8 production records through the event-analysis prompt at both settings, `usage.cost` summed | 2026-09-29 |

## Pipeline code

| # | Change | Before | After | Measured how | Date |
|---|---|---|---|---|---|
| 6 | `podcasts/judge.py` + `xposts/judge.py` → `common/pair_judge.py` | two ~90 %-identical functions (107 + 93 lines); pairs judged **one at a time**, one INSERT per pair, DB session held across the loop; a failed verdict raised `TypeError` in the except (structlog `event=` collision) and killed the run | one function (143 lines incl. both backends); 4 pairs in flight (`JUDGE_CONCURRENCY`), verdicts in one `executemany`; a failed pair logs and is skipped | `tests/test_pair_judge.py` asserts peak in-flight > 1 and exactly one INSERT batch; mutation-verified | 2026-09-22 |
| 7 | Classification write → one conditional `UPDATE … WHERE relevance='pending'` | second `session_scope`: SELECT the row again, mutate, ORM flush (2 round trips); a second worker holding the same item across the model call could overwrite a settled row | 1 round trip; rowcount decides publish; the settled row wins | `tests/test_classification_consumer.py::test_an_item_settled_by_another_worker_mid_call_is_not_overwritten` | 2026-09-22 |

| 8 | `structured_chat` under one deadline; SDK retries 2 → 1 (`common/llm.py`) | worst case per hung call: 3 SDK attempts × 3 parse retries × fallback × 90 s ≈ 13.5 min holding an enrichment slot | ≤ 180 s, then redelivery | `tests/test_hardening_security.py::test_a_hung_provider_costs_one_deadline_not_nine_attempts` | 2026-09-22 |
| 9 | Per-model 429 cooldown (`common/llm.py`) | any model's 429 paused every stage incl. the user-facing Ask stream for 120–900 s | only that model pauses; 401/402/403 stay global | `…::test_a_429_pauses_only_the_model_that_hit_it` | 2026-09-22 |
| 10 | Thread-link verdict writes → `executemany` (`correlation/threads.py`) | up to 15 sequential INSERTs per event (~600 linked events/day ≈ 9k round trips) | 1 round trip per event | code; DB round trips counted | 2026-09-22 |
| 11 | Embedding shadow gate removed | one fastembed call per gated news item (~2,500/day) logging a score nobody consumed | 0 | code; the 2026-07-20 calibration verdict recorded in CHANGELOG 0.0.86.0 | 2026-09-22 |
| 14 | Page fetched unless the feed carries the article (`FULL_BODY_CHARS` 1,500, was 400) | ~1,250 articles in 8 days enriched from a 400–1,500-character summary; TOI 66 words | TOI pages fetched from the worker at 635–984 words; a page shorter than the summary is not kept | prod `articles.retrieval_tier` × feed body length; worker fetch of the same URLs | 2026-09-29 |
| 15 | Headline-list pages refused (`enrichment/fulltext.is_headline_list`) | 26 Aaj Tak short-video pages embedded into one record of unrelated stories | 72/72 short-video pages flagged, plus 5 live blogs and 3 genuine lists in 25,287 pages | 30 days of prod direct-tier text | 2026-09-29 |
| 16 | A permanent failure is given up after 3 dead letters (`ingestion/runner._given_up`) | a refused or invalid extraction re-sent and paid for every 10 min without end | 3 paid attempts, then `relevance='failed'` and a founder email | `tests/test_requeue_giveup.py`, mutation-verified | 2026-09-29 |

## Pending (measured at the time each lands)

Source cache per item; DF-CTE precompute in
`_story_component`; duplicate-URL re-embed; thread-link and ask-guard hybrids
on Jev; web bundle and Lighthouse; SEO levers. See `.claude/plans/product-hardening.plan.md`.
