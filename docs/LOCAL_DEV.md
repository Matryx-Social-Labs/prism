# Local development & observability

Everything now runs and is tested locally against Docker; prod on Railway is a
deploy target, not the dev loop.

## 1. Bring up infra

```bash
docker compose up -d        # postgres (pgvector) + redis
```

## 2. Configure `.env`

`.env` is already on the new schema. Fill in the two blank keys:

- `OPENROUTER_API_KEY` — from https://openrouter.ai/keys (add a few $ of credit).
- `RESEND_API_KEY` — only if you want real email locally; otherwise leave
  `PRISM_EMAIL_PROVIDER=console` and the magic link is printed in the API logs
  (`event="email_console"`).

Confirm the OpenRouter model ids (`PRISM_MODEL_*`) resolve on
https://openrouter.ai/models — free models rotate. Local keeps
`PRISM_INGESTION_ENABLED=false` so no collectors run and no LLM cost accrues
from ingestion; on-demand briefs/Ask/digest still work.

## 3. Run

```bash
alembic upgrade head                       # migrate local DB
uv run uvicorn api.main:app --reload       # API on :8000
uv run python -m worker --stages classification,enrichment,correlation   # pipeline consumers (no ingestion)
cd web && npm run dev                       # frontend on :3000
```

To pull real news once (bypassing the master switch is not needed — just flip it):
set `PRISM_INGESTION_ENABLED=true` and run `uv run python -m worker --stages ingestion`.

## 4. Observability — Langfuse (shared, hosted on Railway)

**Decision: local dev reuses the Railway-hosted Langfuse** rather than running a
second Langfuse stack locally (Langfuse v3 needs postgres + clickhouse + redis +
minio — not worth it). `.env` already points `LANGFUSE_*` at that host, so local
and prod traces land in **one dashboard**. Filter by `environment` / trace
metadata if you need to separate them.

What you get, with no extra code (every LLM call goes through the
`langfuse.openai` wrapper):

- **Traces** — one per pipeline stage / brief / Ask / digest / eval, with the
  prompt, inputs, and output.
- **LLM performance** — model, token counts, and latency per call.
- **Cost** — the OpenRouter model prices are registered in Langfuse (Settings →
  Models), so cost is computed per call/trace automatically. Add a new model's
  price the same way (`POST /api/public/models`) when you introduce one.
- **Prompts** — runtime prompts are managed in Langfuse (`evals/sync_prompts.py`
  publishes the in-repo fallbacks); edit + version there without a deploy.
- **Evals** — `evals/run_all.py` (relevance / classification / threads /
  agent-groundedness) and `evals/brief_groundedness.py` push scores to Langfuse
  Datasets → Runs. Run them locally against the shared instance.

Quick check that tracing works locally: make any request that calls the LLM
(e.g. open a story → a brief generates), then look for the trace in Langfuse.
