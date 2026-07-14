# Per-Story Agent

Every story carries an agent that answers a reader's follow-up questions. The defining constraint
is that it answers from that one event's clustered sources, with citations, and does not assert
beyond them. This is what makes it trustworthy in a market where trust in news is the core problem,
and it matches the fastest-growing news behavior (people using chatbots to ask follow-ups and
evaluate sources).

## Scope
The agent is scoped to a single canonical event. Its retrieval space is the set of articles that
are members of that event (`event_memberships`), plus the event's structured projection (entities,
perspectives, impacts, and, for a cyber story, the CVE and control fields). It does not answer from
the open web or from unrelated events.

## How it works
1. **Grounding set.** Pull the event's member articles and structured fields. Chunk and embed the
   article text (pgvector), or reuse embeddings computed during enrichment.
2. **Retrieve.** For a user question, retrieve the most relevant chunks and structured fields from
   the grounding set only.
3. **Answer with citations.** The model answers using the retrieved context, and every claim is
   tied to the source article ids it came from. The answer records `cited_source_ids` on the
   message.
4. **Refuse gracefully.** If the grounding set does not contain the answer, the agent says so and
   points to what the sources do cover, rather than guessing.

## Suggested and role-aware questions
The agent seeds a few likely questions per story, tuned by the user's role. For a cyber story:
"Does this affect my stack?", "Is it being exploited?", "What should I patch or mitigate?", "Which
of my controls does this touch?". For a general story: "What led to this?", "Who is affected?",
"What are the likely outcomes?", "How is each side framing it?".

## Groundedness evaluation
The agent is evaluated for groundedness: a sample of answers is checked to confirm each claim is
supported by a cited source in the event's grounding set, and that the agent refuses when the
answer is not present. This is the agent analog of the extraction validation and should exist
before the agent is exposed to users.

## Boundaries
- No cross-event or open-web answers in v1. Related events are surfaced by the product's clustering,
  not by the agent wandering.
- No advice that the sources do not support. For the cyber lens, remediation statements come from
  the advisory and control mapping, not invented by the model.
- Every answer is auditable through `cited_source_ids`.
