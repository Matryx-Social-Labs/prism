# ingestion/

The collectors: RSS for news (`rss.py`) and the deterministic CVE feeds (`nvd.py`,
`cisa_kev.py`, off unless the cyber tier is enabled). `runner.py` runs them on the
worker's schedule, canonicalises URLs (`common/urls.py`), drops what was already
seen, writes `raw_items` and emits `raw.items`. `seed.py` seeds the `sources` table (India-first; idempotent).

Master switches, checked before any network call: `PRISM_INGESTION_ENABLED`,
`PRISM_INGEST_MAX_ARTICLES`, and the LLM balance floor (`common/budget.py`).
Details: [docs/PIPELINE.md §3](../docs/PIPELINE.md#3-ingestion); the live outlet list
is `GET /api/v1/sources`.
