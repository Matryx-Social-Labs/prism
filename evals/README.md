# Evals

Gold sets + Langfuse experiments for the pipeline stages that gate quality
(ROADMAP: "do not scale collection before these exist").

## Datasets (`datasets/*.jsonl`)

| File | Dataset name in Langfuse | Measures |
|---|---|---|
| `relevance.jsonl` (27 items) | `prism-relevance` | Relevance-gate binary accuracy |
| `classification.jsonl` (32 items) | `prism-classification` | Sector + role-interest accuracy |
| `agent_groundedness.jsonl` (10 items) | `prism-agent-groundedness` | Groundedness, citation quality, correct refusal (LLM-as-judge) |
| `event_links.jsonl` (8 items) | — | causal / follow-up links between events |
| `story_veto.jsonl` (9 items) | — | the storyline veto's keep / drop calls |

Counts are lines in the file (2026-09-25); the larger labelled sets — event identity,
story boundaries, claims, clips, X posts — live in `tools/gold_*.py` and are scored by
`tools/score_*.py` ([docs/ML-EVALUATION.md](../docs/ML-EVALUATION.md)).

These are starter sets. Grow them from real ingested items: pull borderline
cases from Langfuse traces (Traces → filter by `stage`), label them, and
append. Extraction field-agreement evals are the next addition once a labeled
extraction sample exists.

## Running

```bash
# Everything (uploads datasets, runs experiments, prints scores)
uv run python evals/run_all.py

# One suite
uv run python evals/run_all.py relevance
uv run python evals/run_all.py classification
uv run python evals/run_all.py groundedness
```

Requires `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`, `LANGFUSE_BASE_URL`
(also exported as env vars for the SDK) and `OLLAMA_API_KEY`.

Results land in Langfuse → **Datasets → <name> → Runs**; compare runs after
changing a prompt version or swapping a `PRISM_MODEL_*` env var.

## Baseline (2026-07-15, first recorded run)

| Metric | Score | Notes |
|---|---|---|
| relevance_accuracy | **1.000** | 27 items incl. world-news + finance ground truth |
| sector_accuracy | 0.889 | 18 items |
| role_interest_accuracy | 0.833 | misses are borderline dual-lens items |
| grounded | 0.930 | LLM-as-judge (qwen3.5:397b) |
| citation_quality | 0.920 | |
| correct_refusal | 0.667 → **1.000** (agent-qa v2) | refusal boundary sharpened: no outside knowledge even when confident; partial-answer rule. v2 also lifted grounded to 1.000, citation_quality to 0.947 |

Lens-brief groundedness: spot-checked manually (sanctions story: general +
finance reads correct and grounded; KEV template briefs deterministic). A
formal judge eval for lens briefs is deferred until a labeled sample exists.

## Prompt management

`uv run python evals/sync_prompts.py` publishes the in-repo fallback prompts
(`common/prompts/fallbacks/`) to Langfuse with the `production` label. Iterate
on prompts in the Langfuse UI; the pipeline always fetches the
`production`-labeled version and falls back to the repo copies if Langfuse is
unreachable.
