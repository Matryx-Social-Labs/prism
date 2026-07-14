# Market Research

This is the research that led to the Prism concept and its beachhead choice. It is a point-in-time
snapshot from July 2026. Figures come from the sources listed at the end.

## 1. Market size and momentum
- News aggregator market: about 13.5 billion dollars in 2025, projected to roughly 32 billion
  dollars by 2033, at about 11.2 percent CAGR.
- Mobile news apps market: about 16.9 billion dollars in 2026 to about 24 billion dollars by 2030,
  at roughly 9.3 percent CAGR.
- The single strongest growth driver named across reports is AI-driven content curation, followed
  by real-time delivery and mobile-first consumption.

The category is growing, but it is not a quiet greenfield. The growth is concentrated in exactly
the AI-curation and real-time area where Prism sits.

## 2. Competitive landscape

| Player | What it does | Gap it leaves |
| --- | --- | --- |
| Ground News | Rates every story for media bias (AllSides, Ad Fontes, MBFC); "Blind Spot" shows who is not covering a story | United States left-right axis only; no cross-national framing; no consequence analysis; thin per-story agent |
| Particle (ex-Twitter founders, 10.9M dollar Series A, Lightspeed) | AI multi-source summaries, "Opposite Sides", political-spectrum chart, publisher-friendly linking | Again a US-politics lens; summary-first, not impact-first; general, not role-specific |
| Feedly (Leo AI) | Power-user source control and AI filtering | Built for people who curate their own feeds; not consumer-simple, not both-sides framed |
| AllSides, Straight Arrow | Side-by-side left, center, right | US politics only; editorial, not automated at scale |
| SmartNews, Google News, Apple News | Broad personalized aggregation | No perspective contrast, no consequence layer, no grounded agent |
| Perplexity (Discover plus agentic "Computer") | Conversational answer engine with citations; strong follow-up Q&A | A general answer engine, not a structured news product; no persistent event graph or per-story both-sides framing |
| Artifact (Instagram founders) | Personalized AI feed. Shut down January 2024 | Failed on identity crisis, a market judged too small, and AI disintermediating click-through |
| Benzinga, Bloomberg, AlphaSense, Marketaux | Real-time financial news; Benzinga "Why Is It Moving" plus low-latency API (37 to 79 dollars per month vs Bloomberg terminal at thousands); Marketaux entity-first news | Pro-only, expensive, or developer-facing; no consumer bridge; no cross-perspective narrative |
| GDELT, Event Registry, NewsCatcher, Diffbot | Global article clustering into events with entities and tone; Diffbot knowledge graph | These are pipelines and APIs, not consumer products. They are candidate ingestion suppliers, not competitors |

## 3. Demand signals and risks (Reuters Institute Digital News Report 2026)
- Trust in news is at a record low: about 37 percent globally, about 25 percent in the United
  States. This is the pain a transparent, both-sides, sourced product addresses.
- Weekly use of AI chatbots for news rose from 7 percent in 2025 to 10 percent in 2026, and to 16
  percent among under-35s, mostly for asking follow-ups, summarizing, and evaluating sources. This
  is the fastest-growing behavior and validates the per-story agent.
- Among chatbot users, trust in chatbot-delivered news is higher, at 44 percent, so a well-sourced
  agent can build trust rather than erode it.
- Risks to design around: willingness to pay for news is plateauing, AI is disintermediating
  click-through (the Artifact failure mode), and incumbents own the simple-aggregation layer. The
  wedge cannot be "another personalized feed."

## 4. The gap Prism takes
1. **Cross-national both-sides framing.** Every existing both-sides product frames on the United
   States left-right axis. None systematically contrasts how the parties or countries involved
   frame the same event. Conflict trackers aggregate multiple sources but do not contrast national
   framings. This is the clearest open space.
2. **A consumer-facing consequence layer.** GDELT and Diffbot expose entity graphs to developers,
   but no consumer product tells a reader the downstream impact and likely outcomes for any story.
   This is a direct translation of the EduThreat impact and campaign-correlation idea to general
   news.
3. **A grounded per-story agent.** A story-scoped agent that answers only from that event's
   sources is emerging (Particle, Perplexity) but is not the center of any product.
4. **Role personalization done deeply.** A feed shaped by the user's job role, where each role gets
   its own lens over a shared backbone, is not something the incumbents offer.

## 5. Verdict
The market is growing and crowded at the shallow end, but the combination above is unowned and
defensible. The honest caution is scope, so the plan leads with a single deep vertical
(cybersecurity and GRC) where the team already has an unfair advantage, then expands.

## Sources
- Reuters Institute Digital News Report 2026: https://reutersinstitute.politics.ox.ac.uk/digital-news-report/2026/dnr-executive-summary
- Particle funding and model (Nieman Lab): https://www.niemanlab.org/reading/ai-news-reader-particle-adds-publishing-partners-and-10-9m-in-new-funding/
- Particle brings reader to web (TechCrunch): https://techcrunch.com/2025/05/06/particle-brings-its-ai-powered-news-reader-to-the-web/
- Why Artifact failed (TechCrunch): https://techcrunch.com/2024/01/18/why-artifact-from-instagrams-founders-failed-shut-down/
- Ground News: https://ground.news/
- Benzinga vs Bloomberg (ainvest): https://www.ainvest.com/news/benzinga-bloomberg-25k-37-battle-trader-minds-2601/
- GDELT Cloud: https://gdeltcloud.com/
- News aggregator market size (Future Market Report): https://www.futuremarketreport.com/industry-report/news-aggregator-market/
- Financial news APIs incl. Marketaux (APITube): https://apitube.io/blog/post/best-financial-news-api-trading
