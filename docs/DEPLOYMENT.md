# Deployment Guide — Railway (backend + Langfuse) & Vercel (web)

Everything scriptable lives in the repo (`Dockerfile`, `railway.json`, migrations run
automatically on API start). This guide covers the dashboard steps you click through once;
after that, every push to `main` auto-deploys backend and web.

Topology:

| Piece | Where | Purpose |
|---|---|---|
| `api` service | Railway (this repo) | FastAPI, public domain, runs migrations on boot |
| `worker` service | Railway (this repo) | pipeline consumers + scheduled collectors |
| Postgres (pgvector) | Railway template | canonical store + vector retrieval |
| Redis | Railway | stream spine (Redis Streams) |
| Langfuse | Railway template (separate project) | tracing, prompts, evals |
| Web (Next.js `web/`) | Vercel | the product UI |

---

## Part 1 — Langfuse (self-hosted on Railway)

1. Go to <https://railway.com/deploy> and search for the official **Langfuse v3** template
   (or use the link from <https://langfuse.com/self-hosting/deployment/railway>).
2. Click **Deploy** into a **new Railway project** (name it `langfuse`). The template
   provisions Langfuse web + worker plus its own Postgres, ClickHouse, Redis, and MinIO.
   Keep these separate from Prism's databases — don't share them.
3. Set the template's required secrets when prompted (it generates
   `NEXTAUTH_SECRET`, `SALT`, `ENCRYPTION_KEY` for you — accept or supply your own).
4. When the deploy is green, open the Langfuse web service's **public domain**
   (Settings → Networking → Generate Domain if it doesn't have one).
5. In the Langfuse UI: create your account → create an **Organization** (e.g.
   `matrix-social-labs`) → create a **Project** (e.g. `prism`).
6. Project **Settings → API Keys → Create new key**. Record:
   - `LANGFUSE_PUBLIC_KEY` (pk-lf-…)
   - `LANGFUSE_SECRET_KEY` (sk-lf-…)
   - `LANGFUSE_BASE_URL` = your Langfuse Railway domain, e.g. `https://langfuse-web-production-xxxx.up.railway.app`

Local dev can point at this same instance (put the three values in `.env`).

---

## Part 2 — Prism backend on Railway

### 2.1 Project + databases

1. Create a **new Railway project** named `prism`.
2. **Add Postgres with pgvector**: in the project, `⌘K → Deploy Template` → search
   **"pgvector"** (e.g. *Deploy PgVector*, PG16+). This is Prism's canonical store.
   (The migration runs `CREATE EXTENSION IF NOT EXISTS vector` itself; the template
   image just needs the extension available, which pgvector images are.)
3. **Add Redis**: `⌘K → Database → Redis`.

### 2.2 The `api` service

1. `⌘K → New Service → GitHub Repo` → select **MatrixSocialLab/prism** (grant repo access
   if asked). Railway detects the `Dockerfile` + `railway.json` automatically.
2. Rename the service to `api`.
3. Service → **Settings**:
   - **Networking → Generate Domain** (note it — the web app needs it).
   - Start command: leave empty (Dockerfile default runs migrations + uvicorn).
4. Service → **Variables** (use *References* for the DB/Redis ones):

   | Variable | Value |
   |---|---|
   | `DATABASE_URL` | `postgresql+asyncpg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.RAILWAY_PRIVATE_DOMAIN}}:5432/${{Postgres.PGDATABASE}}` — note the **`+asyncpg`** driver suffix; adjust `Postgres` to your pgvector service's name |
   | `REDIS_URL` | `${{Redis.REDIS_URL}}` |
   | `OLLAMA_API_KEY` | your key from <https://ollama.com/settings/keys> |
   | `LANGFUSE_PUBLIC_KEY` / `LANGFUSE_SECRET_KEY` / `LANGFUSE_BASE_URL` | from Part 1 |
   | `CORS_ORIGINS` | `http://localhost:3000` for now; append `,https://<your-vercel-domain>` after Part 3 (any `*.vercel.app` preview URL is already allowed by the API's regex) |
   | `PRISM_ADMIN_TOKEN` | a long random string (guards `/api/v1/admin/*`) |
   | `NVD_API_KEY` | optional, free from <https://nvd.nist.gov/developers/request-an-api-key> (higher rate limit) |

   Optional model overrides: `PRISM_MODEL_GATE`, `PRISM_MODEL_CLASSIFY`,
   `PRISM_MODEL_EXTRACT`, `PRISM_MODEL_CORRELATE`, `PRISM_MODEL_AGENT`,
   `PRISM_MODEL_JUDGE` (defaults in `.env.example`).

### 2.3 The `worker` service

1. `⌘K → New Service → GitHub Repo` → the **same repo** again. Rename to `worker`.
2. Service → **Settings**:
   - **Start command**: `python -m worker`
   - No public domain needed.
3. **Variables**: same set as `api` (Railway shared variables help here), plus optionally
   `PRISM_INGEST_INTERVAL_MINUTES` (default `30`).

### 2.4 Verify

- Both services deploy green; `https://<api-domain>/healthz` returns `{"status":"ok"}`.
- Worker logs show `prism worker starting` and an ingestion run.
- `https://<api-domain>/api/v1/feed` returns events after the first run (~2–5 min).
- Auto-deploy: push any commit to `main` → both services rebuild (watch paths in
  `railway.json` skip rebuilds for `web/`-only changes).

---

## Part 3 — Web app on Vercel

1. <https://vercel.com/new> → Import **MatrixSocialLab/prism**.
2. **Root Directory**: `web` (critical — the Next.js app lives there).
   Framework preset: Next.js (auto-detected).
3. **Environment variables**:

   | Variable | Value |
   |---|---|
   | `NEXT_PUBLIC_API_URL` | `https://<your-railway-api-domain>` |

4. Deploy. Every push to `main` now redeploys production; PRs get preview deploys.
5. Back in Railway → `api` service → append your production Vercel domain to
   `CORS_ORIGINS` (comma-separated). Preview `*.vercel.app` domains are already
   covered by the API's built-in regex.

---

## Part 4 — Wire Langfuse into your workflow

- **Traces**: Langfuse UI → Traces — every pipeline stage (`relevance-gate`,
  `classifier`, `extract-shared`, `perspective-impact`, `agent-qa`) appears with model,
  tokens, and latency. Agent chats group under Sessions.
- **Prompts**: run `uv run python evals/sync_prompts.py` once (locally, with the
  Langfuse env vars set) to publish the versioned prompts with the `production` label.
  After that, edit/iterate prompts in the Langfuse UI — the pipeline picks up the
  `production`-labeled version, falling back to the in-repo copies if Langfuse is down.
- **Evals**: `uv run python evals/run_all.py` uploads the gold datasets and runs
  experiments (see `evals/README.md`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| API 500s with `InvalidPasswordError` / connection refused | Check `DATABASE_URL` reference points at the pgvector service and includes `+asyncpg` |
| `extension "vector" is not available` | The Postgres service isn't a pgvector image — redeploy using a pgvector template |
| Feed is empty | Check worker logs for collector errors; trigger manually: `curl -X POST -H "X-Admin-Token: $PRISM_ADMIN_TOKEN" https://<api-domain>/api/v1/admin/pipeline/run` |
| No traces in Langfuse | Verify the three `LANGFUSE_*` vars on **both** services; keys are project-scoped |
| Ask agent errors | Verify `OLLAMA_API_KEY`; check Ollama Cloud usage limits (5-hour session / weekly caps) |
| Web can't reach API | `NEXT_PUBLIC_API_URL` has no trailing slash; CORS_ORIGINS includes your Vercel domain |
