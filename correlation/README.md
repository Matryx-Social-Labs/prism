# correlation/

Consumes `enriched.items` and turns reports into the record: events, their analysis,
and the stories they belong to.

- `clustering.py` — the **event match cascade**: CVE id → canonical URL → title trigram →
  English headline (off) → embedding → shared actors → **verified** (gist candidates
  judged by Jev). Every distance lives in one per-model table, `_SCALE`.
- `verify.py` — the verified tier's judge and verdict log (`event_match_verdicts`)
- `consumer.py` — attach or found an event under one advisory lock; canonical title
  (Prism's English headline); entity upsert and fold; projection rebuild; the debounced
  analysis sweeper (perspectives, impacts, lens briefs)
- `threads.py` — causal and follow-up links between events (`event_links`)
- `partition.py` — the story layer: mutual-kNN graph, Leiden (CPM), the branch tree
- `trending.py` — story reconciliation, `merged_into` + redirects, velocity
- `briefs.py`, `cites.py`, `digest.py` — lens briefs, brief citation checks, Market Pulse

How events are decided and measured: [docs/CANONICALIZATION.md](../docs/CANONICALIZATION.md).
Stage by stage: [docs/PIPELINE.md §6–7](../docs/PIPELINE.md#6-correlation--the-event-match-cascade).
