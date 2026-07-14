# Evals

Gold sets + Langfuse experiments for the pipeline stages that gate quality
(ROADMAP: "do not scale collection before these exist").

## Datasets (`datasets/*.jsonl`)

| File | Dataset name in Langfuse | Measures |
|---|---|---|
| `relevance.jsonl` (20 items) | `prism-relevance` | Relevance-gate binary accuracy |
| `classification.jsonl` (16 items) | `prism-classification` | Sector + role-interest accuracy |
| `agent_groundedness.jsonl` (10 items) | `prism-agent-groundedness` | Groundedness, citation quality, correct refusal (LLM-as-judge) |

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

## Prompt management

`uv run python evals/sync_prompts.py` publishes the in-repo fallback prompts
(`common/prompts/fallbacks/`) to Langfuse with the `production` label. Iterate
on prompts in the Langfuse UI; the pipeline always fetches the
`production`-labeled version and falls back to the repo copies if Langfuse is
unreachable.
