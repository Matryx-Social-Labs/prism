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

## Microservice architecture on Railway

**The topology above already is a microservice architecture.** Each concern is its own
Railway service with its own lifecycle, logs, metrics, restarts, and scaling: the API,
the pipeline worker, Postgres, Redis, and the whole Langfuse stack. Services talk only
through two contracts — the database and the Redis Streams topics — never in-process,
which is exactly the seam microservices need.

### Recommended: start with 2 app services, split when a signal appears

For the prototype's volume (a few thousand items/day), run **`api` + one `worker`**.
Finer splits add per-service cost (Railway bills per service), more env vars to keep in
sync, and more deploys to watch — with no benefit until one stage becomes a bottleneck.

Split when you see one of these signals:

| Signal | Split to make |
|---|---|
| Enrichment backs up (embedding CPU saturates the worker) | dedicated `enrichment` service, more CPU |
| LLM stage slowness starves the collectors | `ingestion` separated from LLM stages |
| A stage needs different scaling (e.g. many classification replicas during a backfill) | that stage as its own service with replicas |

### How to split (already supported — no code changes)

The worker takes a `--stages` flag (or `PRISM_STAGES` env var), so each pipeline stage
can be its own Railway service from the same repo/image:

| Railway service | Start command |
|---|---|
| `ingestion` | `python -m worker --stages ingestion` |
| `classification` | `python -m worker --stages classification` |
| `enrichment` | `python -m worker --stages enrichment` |
| `correlation` | `python -m worker --stages correlation` |

Each service gets the same variable set as `worker` (use Railway **Shared Variables**
so they stay in sync). Because every stage is an idempotent Redis Streams consumer
group, you can also scale **replicas** of a single stage — set a unique
`PRISM_CONSUMER_NAME` per replica (e.g. reference Railway's `RAILWAY_REPLICA_ID`) so
the consumer-group members don't collide.

Postgres and Redis stay as single shared services — they are the stateful contracts,
not microservices to multiply. When volume outgrows Redis Streams, the swap is
Kafka/Redpanda behind `common/stream.py`, not more Railway services.

---

## Railway CLI (setup once, then validate anything)

The dashboard steps below can also be done — and later verified — with the
[Railway CLI](https://docs.railway.com/guides/cli):

```bash
npm i -g @railway/cli    # or: brew install railway
railway login            # opens browser
railway link             # run inside the repo → pick the prism project + environment
```

Useful commands once linked:

```bash
railway status                      # project / environment / linked service
railway logs --service api         # live logs (also: --service worker)
railway variables --service api    # list env vars
railway variables --service api --set "CORS_ORIGINS=https://your-app.vercel.app,http://localhost:3000"
railway up --service api           # deploy local code directly (bypasses GitHub)
railway redeploy --service worker  # restart with the latest image
railway run python -c "..."        # run a one-off command with the service's env vars
railway connect Postgres           # psql shell into the database
```

After you've created the project and linked it, validation is:
`railway status` → both services green; `railway logs --service worker` → shows
`prism worker starting` + ingestion runs; `curl https://<api-domain>/healthz` → ok.

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

1. `⌘K → New Service → GitHub Repo` → select **Matryx-Social-Labs/prism** (grant repo access
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

## Part 3 — Web app on Vercel (CLI deploy from GitHub Actions)

**Why CI instead of the Vercel GitHub integration:** the Hobby plan blocks the
GitHub integration on private organization repos, and it only accepts deploys
whose commit author email matches the Vercel account owner. The workflow in
`.github/workflows/ci.yml` solves both (same pattern as routeHer/safera): it
deploys via the Vercel CLI on every push to `main`, and re-authors HEAD inside
the runner to `contact@matrixsociallabs.com` — the Vercel account email — so
the owner check passes no matter who authored the commit. The re-author is
local to the runner; GitHub history is never rewritten. Deploys run only after
the backend and web verify jobs are green.

### 3.1 One-time Vercel project setup (local machine)

```bash
npm i -g vercel
vercel login                    # log in as contact@matrixsociallabs.com
cd <repo-root>
vercel link                     # create/link project: scope = the account, name = prism
```

Then in the Vercel dashboard → project **Settings**:
- **Root Directory**: `web` (critical — the Next.js app lives there)
- **Environment Variables** (Production): `NEXT_PUBLIC_API_URL` =
  `https://<your-railway-api-domain>` (no trailing slash)

`vercel link` writes `.vercel/project.json` locally (gitignored) containing the
two IDs you need next:

```bash
cat .vercel/project.json   # → {"orgId":"...","projectId":"..."}
```

### 3.2 GitHub secrets

Create a token at <https://vercel.com/account/settings/tokens> (scope: the
account that owns the project; no expiry or 1 year). Then add the three
secrets — either in GitHub UI (repo → Settings → Secrets and variables →
Actions → New repository secret) or via the CLI:

```bash
gh secret set VERCEL_TOKEN      --repo Matryx-Social-Labs/prism   # paste the token
gh secret set VERCEL_ORG_ID     --repo Matryx-Social-Labs/prism   # orgId from project.json
gh secret set VERCEL_PROJECT_ID --repo Matryx-Social-Labs/prism   # projectId from project.json
```

| Secret | Where it comes from |
|---|---|
| `VERCEL_TOKEN` | vercel.com → Account Settings → Tokens → Create |
| `VERCEL_ORG_ID` | `.vercel/project.json` → `orgId` (starts `team_` or user id) |
| `VERCEL_PROJECT_ID` | `.vercel/project.json` → `projectId` (starts `prj_`) |

### 3.3 How the workflow behaves

- **Every push / PR**: `backend` (ruff + import check + tests) and `web`
  (Next.js production build) must pass.
- **Push to `main` only**: `deploy-web` re-authors HEAD, runs
  `vercel pull → vercel build --prod → vercel deploy --prebuilt --prod`,
  and prints the deployment URL in the run summary. Production deploys are
  serialized so rapid pushes don't race.
- Pushing workflow files requires the `workflow` OAuth scope:
  `gh auth refresh -h github.com -s workflow` once, if a push is rejected
  with "refusing to allow an OAuth App to … workflow".

### 3.4 After the first deploy

Back in Railway → `api` service → append your production Vercel domain to
`CORS_ORIGINS` (comma-separated). Preview `*.vercel.app` domains are already
covered by the API's built-in regex:

```bash
railway variables --service api --set "CORS_ORIGINS=http://localhost:3000,https://<your-app>.vercel.app"
```

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
| Traces missing but prompts/API work (SDK logs `Internal Server Error … exporting span batch`) | The Langfuse **ingestion chain** is down inside the Langfuse Railway project: trace writes go web → MinIO (S3 event upload) → Redis → worker → ClickHouse, while prompt/read APIs only need Postgres. In the `langfuse` Railway project check that **MinIO, Redis, ClickHouse, and langfuse-worker** are all green, then check the langfuse-web logs for S3/bucket errors (`LANGFUSE_S3_EVENT_UPLOAD_*` vars must point at the MinIO service and the bucket must exist). Restart MinIO + worker after fixing. Verify with `curl -s -X POST <langfuse-url>/api/public/ingestion -u pk:sk -H 'Content-Type: application/json' -d '{"batch":[{"id":"t1","type":"trace-create","timestamp":"<now-iso>","body":{"id":"tr1","name":"smoke","timestamp":"<now-iso>"}}]}'` — expect a 207, not a 500 |
| Ask agent errors | Verify `OLLAMA_API_KEY`; check Ollama Cloud usage limits (5-hour session / weekly caps) |
| Web can't reach API | `NEXT_PUBLIC_API_URL` has no trailing slash; CORS_ORIGINS includes your Vercel domain |
