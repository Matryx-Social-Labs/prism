# classification/

Consumes `raw.items`. Decides whether an item is news worth keeping (the relevance
gate), then its sector, subsector, subject path, regions and fast-lane routing, and
emits `classified.items` for the relevant ones.

Two backends, one contract (`GateResult` + `ClassificationResult`):
- the LLM pair — a gate call and a classifier call (`consumer.py`)
- **Jev** — one typed Decisions call answering ten questions (`decide.py`), selected by
  `PRISM_DECISIONS_MODE=off|shadow|live` (**live** in production); thresholds are set
  from labels, not 0.5

`subject.py` maps into the reader-facing subject tree. Details and thresholds:
[docs/PIPELINE.md §4](../docs/PIPELINE.md#4-classification); measurements:
[docs/ML-EVALUATION.md](../docs/ML-EVALUATION.md).
