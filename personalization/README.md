# personalization/

The per-user layer. Consumes `event.updates`, selects each user's role lens from their profile,
scores new events with a relevance and ranking model (`user_event_scores`), assembles the ranked
feed (`feed_items`), and drives alerts and the real-time fast-lane. Emits `feed.updates`.

See [../docs/PERSONAS.md](../docs/PERSONAS.md) and [../docs/DB-SCHEMA.md](../docs/DB-SCHEMA.md).
