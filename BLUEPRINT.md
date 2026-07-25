# Parse — Blueprint

A one-page strategic summary. The full research report lives in
[docs/MARKET-RESEARCH.md](./docs/MARKET-RESEARCH.md); the build detail lives in the other docs.

## The concept
A role-aware AI news intelligence platform for everyone — not a niche professional tool.
Onboarding captures how each user reads the world (a professional role, or general reader), and
that drives a personalized feed in which every story receives the same end-to-end treatment:
multi-perspective framing, related news clustered, correlation and impact analysis, per-lens
written briefs (the same event as threat forecast, market catalyst, or plain account — switchable
on any story), and a grounded question-answering agent.

## The promise, per story
1. **Both Sides.** Who is saying what, including sources from the countries or parties involved,
   grouped by stance and by origin, so a reader sees how the same event is framed from each side.
2. **So What.** The impact and consequence graph: which organizations, companies, and people are
   affected, and the likely second-order outcomes, for any story from geopolitics to sports.
3. **Ask.** A per-story agent that answers follow-up questions using only that event's clustered
   sources, with citations.

## Why now
News trust is at a record low (about 37 percent globally, about 25 percent in the United States),
while the use of AI chatbots for news is rising fast (7 to 10 percent weekly year on year, 16
percent for under-35s) mostly for follow-up questions and evaluating sources. A transparent,
sourced, both-sides product with a grounded agent answers that exact demand. See the research doc
for figures and sources.

## The gap we take
The market is crowded at the simple-aggregation layer, but no one owns the combination of
cross-national both-sides framing, a consumer-facing consequence graph, and a grounded per-story
agent. Existing both-sides products (Ground News, Particle) frame only on the United States
left-right axis; developer graph tools (GDELT, Diffbot) never reach the consumer; financial tools
(Benzinga, Bloomberg) are pro-only and expensive.

## The one risk we design around
Trying to build all news for everyone at once is what sank Artifact (Instagram founders, shut down
2024). The answer is a single deep vertical first, then horizontal expansion by adding role lenses
on the same backbone.

## Confirmed decisions
| Decision | Choice |
| --- | --- |
| Beachhead role | Cybersecurity and GRC (CVE and security news, with a read on controls) |
| Monetization | Prosumer subscription (individual professionals) |
| Ingestion | Hybrid: news-event APIs for breadth, NVD/CVE and CISA KEV for cyber depth, a few own collectors ported from EduThreat |
| Stack | Fresh, streaming-first (new repo, not a fork); patterns ported from EduThreat |

## Phasing
- **Phase 1 (beachhead):** the full experience for cybersecurity and GRC.
- **Phase 2:** add the finance and trader lens (real-time fast-lane) on the same backbone.
- **Phase 3:** open personalization to general roles and sectors; add a prosumer graph and API;
  later, B2B team seats.

## Open naming and scope questions (not blockers)
- Final product name (working codename "Parse").
- Exact streaming backbone (Kafka/Redpanda vs NATS) and search store.
- Which news-event API to license first, and the initial region and language priority.
- Whether this also seeds a second research paper, which would raise the measurement rigor baked
  into the pipeline from day one.
