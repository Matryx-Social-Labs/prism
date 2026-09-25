# agent/

**Ask** — per-story grounded question answering. The retrieval space is the story's
own member article chunks (pgvector over `article_chunks`) plus its structured
projection; answers cite reports inline as `[n]`, cited ids are kept on
`agent_messages.cited_source_ids`, and when the reports do not say, the agent says so.

- `rag.py` — retrieval, grounding, streaming answer (`POST /api/v1/events/{id}/ask`, SSE)
- `structure.py` — the held-back tail after the prose: what the reports don't say, follow-ups, one table
- `questions.py` — suggested questions per story from lens templates (no LLM spend per view)

Limits (plan allowance, burst, daily spend ceiling): [docs/API.md](../docs/API.md#events--detail-briefs-questions-ask-apirouteseventspy).
Design and guardrails: [docs/AGENT.md](../docs/AGENT.md). Wiring: [docs/PIPELINE.md §8](../docs/PIPELINE.md#8-side-channels).
