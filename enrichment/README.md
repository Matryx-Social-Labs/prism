# enrichment/

Consumes `classified.items`; emits `enriched.items`. Per article:

1. **Full text** (`fulltext.py`) — direct fetch, feed body, title, or an earlier
   extraction of the same URL (paid once per URL)
2. **Extraction** (`schemas.py`, prompt `extract-shared`) — an English headline and
   one-line summary in every language, a reader brief, entities, regions, claims, and
   lens fields (cyber, finance with tickers validated against listed securities)
3. **Verbatim or not stored** (`claims.py`) — a quote is kept only if its exact words
   are found in the article
4. **Embeddings** — the text chunked and embedded with `multilingual-e5-base`, plus the
   **gist** (English headline + summary) that the verified matching tier retrieves on
5. **Photo fingerprint** — a dHash of the lead image, so repeats and outlet fallback art
   can be recognised

`cve_lens.py` handles the deterministic NVD/CISA-KEV records; `renderings.py` judges
translated quotes. Details: [docs/PIPELINE.md §5](../docs/PIPELINE.md#5-enrichment).
