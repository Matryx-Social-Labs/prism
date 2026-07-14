# agent/

The per-story question-answering agent. Retrieval-augmented over a single event's clustered sources
and structured fields (pgvector), answers with citations (`cited_source_ids`), and refuses when the
answer is not in the grounding set. Seeds role-aware suggested questions.

See [../docs/AGENT.md](../docs/AGENT.md).
