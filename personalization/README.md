# personalization/

`ranking.py` — per-lens feed scoring: lens-weighted recency decay (from when the event
happened, not when it was ingested) plus lens-specific boosts, corroboration and the
reader's languages. Every story row carries this `score` (`api/routes/serialization.py`);
the feed orders by it when sorted by `top`.

Per-user models (`user_event_scores`, a `feed.updates` stream) were planned in July and
are **not built**; a reader's interests filter and their languages rank the feed
(`api/routes/feed.py`). See [docs/PIPELINE.md §8](../docs/PIPELINE.md#8-side-channels).
