# classification/

The relevance gate and the classifier/router. Consumes `raw.items`, drops non-stories with a binary
LLM gate, tags sector, regions (countries involved), language, and role interests, sets the routing
decision (standard vs fast-lane), and emits `classified.items`. Rejected items are kept with a
reason for audit.

See [../docs/INGESTION-CLASSIFICATION.md](../docs/INGESTION-CLASSIFICATION.md).
