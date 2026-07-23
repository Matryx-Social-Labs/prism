# How-to guides

Task-focused recipes for extending and operating Prism. Each assumes you have the
app running locally ([TUTORIAL.md](./TUTORIAL.md)) and know the layout
([ARCHITECTURE.md](./ARCHITECTURE.md)). For the "why" behind these systems, see
[STORY-GRAPH.md](./STORY-GRAPH.md).

- [Add an RSS source](#how-to-add-an-rss-source)
- [Add a lens](#how-to-add-a-lens)
- [Add a language](#how-to-add-a-language)
- [Trigger an ingestion run](#how-to-trigger-an-ingestion-run)
- [Inspect the production database](#how-to-inspect-the-production-database)
- [Run the tests](#how-to-run-the-tests)

---

## How to add an RSS source

Add a news feed so its articles flow through ingest → classify → enrich → cluster.

### Steps
1. Add a `FeedSpec` to `FEEDS` in `ingestion/rss.py`:
   ```python
   FeedSpec("deccanherald_karnataka",
            "https://www.deccanherald.com/rss/karnataka.xml",
            sector=None, region="IN-KA"),
   ```
   `slug` must be unique. Set `region` to an ISO 3166-2 code for a state edition;
   leave `sector`/`subsector` unset unless the feed is single-topic.

2. Register the outlet in `SOURCES` in `ingestion/seed.py` (this is the row the
   provenance/transparency chips read):
   ```python
   {"slug": "deccanherald_karnataka", "name": "Deccan Herald — Karnataka",
    "source_type": "rss", "country": "IN", "language": "kn"},
   ```
   Add `"reliability": {"funding": "public"}` for public broadcasters.

3. Seed the new source row:
   ```bash
   uv run python -c "import asyncio; from ingestion.seed import seed_sources; asyncio.run(seed_sources())"
   ```

### Verification
Trigger a run (below) and confirm rows appear:
```bash
uv run python -c "import asyncio; from ingestion.rss import collect; print(asyncio.run(collect()))"
```
It prints the number of new raw items. Check `raw_items` for `source_id` matching
the new slug.

### Troubleshooting
- **No items** — the feed URL may be wrong or return < `MIN_USEFUL_CHARS` bodies;
  the fetcher falls back to trafilatura on the article URL. Verify the URL in a
  browser first.
- **Slug collision** — `seed_sources` is `ON CONFLICT DO NOTHING`; rename the slug.

---

## How to add a lens

A lens is a declarative role — a slug, the sectors it cares about, its ranking
weights, and its questions. It is never a new pipeline.

### Steps
1. Add an entry to `LENSES` in `common/lenses.py`:
   ```python
   "legal": Lens(
       slug="legal",
       name="Legal / Compliance",
       tagline="Rulings, precedent, and what it changes",
       role_interest="legal",
       sectors=["politics"],              # [] = all sectors
       ranking=RankingWeights(recency=1.2, corroboration=0.1),
       suggested_questions=["What precedent does this set?", …],
       upcoming=True,                     # drafted: kept in the registry, not served
   ),
   ```
2. Flip `upcoming=False` when it ships. Only non-`upcoming` lenses are returned by
   `GET /api/v1/lenses` and can activate extraction/gating.
3. Give it a hue in `web/src/lib/lenses.ts` (colour = a lens speaking; see
   [DESIGN.md](../DESIGN.md)).

### Verification
```bash
curl -s localhost:8000/api/v1/lenses | jq '.lenses[].slug'   # your slug appears
curl -s "localhost:8000/api/v1/feed?lens=legal" | jq '.lens' # echoes "legal"
```

### Troubleshooting
- **Feed comes back cyber-only / wrong sectors** — check `sectors`. `[]` means all
  sectors (the reader default); a specific list restricts the feed. `DEFAULT_LENS`
  must stay `reader` so a missing/unknown lens falls back to all news, not one
  sector.

---

## How to add a language

Languages rank and localize the feed; they never filter it.

### Steps
1. Add to `LANGUAGES` in `common/languages.py` (code + English name + native
   script) and, to offer it at launch, to `LAUNCH_LANGUAGES`:
   ```python
   "ta": Language(code="ta", name="Tamil", native="தமிழ்"),
   ```
2. Add native short labels for the UI in `web/src/lib/languages.ts`
   (`LANG_NATIVE` + `LANG_NAME`) — the feed language chip and per-card headline
   tag read these.
3. Add feeds in that language ([add an RSS source](#how-to-add-an-rss-source)) so
   there is coverage to rank.

### Verification
```bash
curl -s localhost:8000/api/v1/languages | jq '.languages[].code'
curl -s "localhost:8000/api/v1/feed?languages=ta,en" | jq '.items[0].headline_lang'
```

### Troubleshooting
- **Headlines never tag as Tamil** — the API sets `headline_lang` only when the
  served headline came from a language-tagged headline in `projection.headlines[]`.
  The frontend also falls back to Unicode-script detection, so a Tamil-script
  headline tags even when the API returns `null`.

---

## How to trigger an ingestion run

The API never ingests in-process; the worker owns collection. Two ways to run it.

### Locally (worker process)
```bash
uv run python -m worker                    # all stages + scheduled collectors
uv run python -m worker --stages ingestion # collectors only
```
The worker kicks off one ingestion run at startup, then every
`PRISM_INGEST_INTERVAL_MINUTES` (default 30).

### On demand (admin trigger, prod or local)
```bash
curl -X POST localhost:8000/api/v1/admin/pipeline/run \
  -H "X-Admin-Token: $PRISM_ADMIN_TOKEN"
```
This enqueues a run over the Redis stream; overlapping triggers coalesce behind one
lock.

### Verification
Watch the worker logs for `collector_run` then the stage consumers
(`classification` → `enrichment` → `correlation`). New events appear in the feed.

### Troubleshooting
- **Nothing enriches, logs show `llm quota exhausted (402)`** — the LLM provider is
  out of credits. Ingestion and CVE records keep flowing (deterministic), but LLM
  classification/enrichment pause and retry on cooldown; items stay queued (no data
  loss) and drain when credits return.

---

## How to inspect the production database

Prod Postgres is reachable over Railway's public TCP proxy with `asyncpg`.

### Steps
1. Get the proxy connection info (values are secrets — do not commit):
   ```bash
   railway variables --service Postgres --kv | grep -E 'PGPASSWORD|RAILWAY_TCP_PROXY'
   ```
2. Connect and query:
   ```python
   import asyncpg, asyncio, os
   async def main():
       c = await asyncpg.connect(
           f"postgresql://postgres:{os.environ['PGPASSWORD']}"
           f"@{os.environ['RAILWAY_TCP_PROXY_DOMAIN']}:{os.environ['RAILWAY_TCP_PROXY_PORT']}/railway")
       print(await c.fetch("SELECT slug, label, source_count FROM stories "
                           "WHERE merged_into IS NULL AND status='active' ORDER BY velocity DESC"))
   asyncio.run(main())
   ```
   To run app code (e.g. `story_timeline`) against prod, build a
   `postgresql+asyncpg://` URL with the password URL-encoded and set it as
   `DATABASE_URL` before importing `common.db`.

### Troubleshooting
- **`password authentication failed`** — the table view wraps long values; use
  `--kv` (key=value) output, not the ASCII table.
- **`cannot cast jsonb to text[]`** — `member_event_ids` / `cast` are JSONB; parse
  with `json.loads` in Python rather than casting in SQL.

---

## How to run the tests

```bash
uv run pytest -q                    # full suite
uv run pytest tests/test_trending.py -q
uv run ruff check .                 # lint (CI gate)
cd web && npm run build             # frontend typecheck + build (CI gate)
```
DB-dependent tests skip automatically when no database is reachable. CI runs
`ruff` + `pytest` + `next build` on every PR; the route surface is guarded by
`tests/test_api_routes.py`.

## Related
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Railway + Vercel deploy, gated backend approval.
- [LOCAL_DEV.md](./LOCAL_DEV.md) — infra + observability setup.
- [STORY-GRAPH.md](./STORY-GRAPH.md) — the systems these recipes extend.
