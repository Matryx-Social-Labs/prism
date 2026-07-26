# Tutorial: run Parse locally and flip a lens

By the end of this you'll have the full Parse pipeline running on your machine,
real stories in the feed, and you'll have watched one story re-typeset itself as
you switch lenses — the thing Parse exists to do. You do **not** need an LLM key to
get started: CVE feeds flow end to end with deterministic enrichment, so you'll see
real cybersecurity stories within a few minutes. A key unlocks news and the
lens-flip brief later in the tutorial.

## What you'll need
- **Docker** (for Postgres + Redis)
- **Python 3.12+** with [uv](https://docs.astral.sh/uv/)
- **Node 20+**
- Optional, for news + lens briefs: an **Ollama Cloud** API key (`OLLAMA_API_KEY`)

---

## Step 1: Bring up infra and the schema

```bash
cp .env.example .env           # defaults work for local; leave OLLAMA_API_KEY blank for now
docker compose up -d           # Postgres (pgvector) + Redis
uv sync                        # Python deps
uv run alembic upgrade head    # create the schema
```
You now have an empty database with the full schema and two message queues (Redis
Streams) ready. Nothing is running yet.

## Step 2: Start the three processes

Open three terminals:

```bash
# terminal 1 — the pipeline worker (ingests on start, then every 30 min)
uv run python -m worker

# terminal 2 — the API
uv run uvicorn api.main:app --reload

# terminal 3 — the web app
cd web && npm install && npm run dev
```

## Step 3: See the app

Open **http://localhost:3000**. You'll see the Parse landing page ("One story.
Every perspective."). Click **Browse the news** → the feed. It may be sparse for a
moment — the worker started ingesting the instant it launched.

That's your first visible result. Now let's get real stories into it.

## Step 4: Watch CVE stories flow in (no LLM key needed)

In terminal 1 (the worker), you'll see the pipeline move:
```
collector_run  collector=rss:...        new=…
collector_run  collector=nvd            new=…
… classification … enrichment … correlation …
```
CISA KEV and NVD records enrich **deterministically** — no LLM. Within a minute or
two, hit the API directly:

```bash
curl -s "http://localhost:8000/api/v1/feed?lens=cyber&limit=5" | \
  python3 -c "import sys,json; [print('•', i['title'][:70]) for i in json.load(sys.stdin)['items']]"
```

The cyber lens is the one that lets raw CVE records in, so you'll see them here.
Once there's journalism to weave them between they hold to one record per two
stories; this early, with only the deterministic feeds ingesting, records are
most of what exists, so that's most of what you get. It is still a whole-world
feed either way: a lens **ranks**, it never filters, so cyber-relevant items rise
to the top while elections and markets stay on the page. (Want cybersecurity only?
That's `?sector=cybersecurity`.)

Reload the feed in the browser with the **Cyber** lens (set it in "Your Parse" via
the onboarding flow, or query `?lens=cyber` on the API). You're looking at real,
clustered, freshly-ingested stories.

## Step 5: Open a story

Click any story. The story view shows the header, the **sources** (each with its
outlet and stance), **entities**, and the **story timeline** — every development of
this story, chronological. For a CVE story you'll also see CVSS, exploitation
status, and affected products. This is the canonical event assembled from every
outlet that covered it (see [STORY-GRAPH.md](./STORY-GRAPH.md)).

## Step 6: Flip the lens

This is the payoff. Add your `OLLAMA_API_KEY` to `.env` and restart the worker and
API (news items and lens briefs both need the model):

```bash
# .env
OLLAMA_API_KEY=your-key-here
```

Trigger a fresh run so news (not just CVEs) flows in:
```bash
curl -X POST localhost:8000/api/v1/admin/pipeline/run -H "X-Admin-Token: $PRISM_ADMIN_TOKEN"
```

Open a story that has more than one lens available and switch the **lens tabs**
(Reader / Cyber / Markets). The **brief** re-inks: the same event, read for a
different role — a general reader's "what led to this and who's affected", a
security professional's "who's exposed, what to patch", a trader's "which tickers,
what catalyst". The body and layout don't move; only the meaning does. That is
Parse.

---

## What you built
You ran the whole thing: ingestion → relevance gate → classification → enrichment →
clustering → correlation → lens briefs → serving, plus the Next.js app. You watched
duplicate coverage collapse into one canonical story and then re-read that story
through multiple professional lenses.

Next:
- **Extend it** — [HOWTO.md](./HOWTO.md): add a source, a lens, or a language.
- **Understand it** — [STORY-GRAPH.md](./STORY-GRAPH.md) (how stories form),
  [ARCHITECTURE.md](./ARCHITECTURE.md) (the streaming pipeline).
- **Query it** — [API.md](./API.md): the full HTTP surface.
- **Ship it** — [DEPLOYMENT.md](./DEPLOYMENT.md): Railway + Vercel.

## Troubleshooting
- **Feed stays empty** — check terminal 1 for `collector_run`. RSS/GDELT news needs
  `OLLAMA_API_KEY`; without it only CVE feeds (cyber lens) populate. Confirm
  Postgres and Redis are up (`docker compose ps`).
- **`alembic upgrade` fails** — Postgres isn't ready yet; wait a few seconds after
  `docker compose up -d` and retry.
- **Lens brief says "not available yet"** — the brief is an on-demand LLM call; set
  `OLLAMA_API_KEY` and it generates on first view (then caches).
