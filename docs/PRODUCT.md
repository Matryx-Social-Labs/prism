# Parse — Product placement

*One story. Every perspective.* Role-aware AI news intelligence for everyone.

## The problem

News is fragmented three ways: **duplication** (fifty headlines for one event), **framing** (each
outlet tells its side; most readers only ever see the coverage of one country's media), and
**relevance** (a war is a humanitarian story, a cyber-risk window, and a market catalyst at once —
but every publication picks one framing and discards the rest).

## What Parse is

A pipeline that clusters worldwide coverage into **canonical events**, then serves each event
through **professional lenses**:

1. **Neutral core** — title, summary, sources with field-level provenance, Both-Sides perspective
   groups, consequence graph, and a grounded per-story agent that cites or refuses.
2. **Lens briefs** — written analysis of the same event through the reader's professional lens
   (cyber/GRC, markets, general reader today; lenses are registry entries, not new pipelines).
   Only lenses with a genuine distinct read are offered per story.
3. **Personalization without accounts** — region + profession + sector/sub-domain interests
   (sports → cricket, technology → AI…) live in the browser; the feed blends international and
   regional coverage, latest-first.
4. **Event threads** — cross-event causal links surfaced in real time: a war → shipping halts →
   oil-price coverage, each hop cited to the stories that evidence it ("what led here / what
   followed / what to expect").

## Breaking one-sided coverage (the mission)

Global news framing is dominated by a handful of media systems; the other side of a story often
never reaches the reader. Parse measures balance on an **origin-country axis** — not the US
left/right axis Ground News uses:

- Sources span origins deliberately: IN (7 outlets), GB, QA, DE, FR, TR, HK, PK, RU, CN, IR + GDELT.
- State-affiliated and publicly funded outlets are **included and labeled** ("State-affiliated",
  "Public broadcaster") — readers see every side *and* who is speaking.
- Every story carries its **coverage-origin distribution** (which countries' media covered it,
  how many outlets each) and a **single-origin blindspot flag** when only one country's media
  is telling the story.
- Perspectives group coverage by origin and stance so the framings can be read side by side.

## India-first wedge

The first target audience is the Indian reader: dense regional source coverage (The Hindu, TOI,
NDTV, Hindustan Times, Mint, BusinessLine, ESPNcricinfo), cricket and entertainment sub-domains
that mainstream news intelligence ignores, a GDELT India query, region-aware feed scoping
(All / India / World), and Singapore hosting for latency. Indian English-language news is
globally under-served by aggregation products that treat "world news" as US/UK news.

## Personas

- **The reader** — keep me informed: world + my region, my interests, both sides, ask anything.
- **Cyber/GRC professional** — the beachhead depth: CVEs with CVSS/KEV/affected products/control
  mappings, plus the cyber read of world events (who is exposed, what to check).
- **Trader/analyst** — tickers, catalysts, evidence-based price reads, second-order effects.
- Future lenses (policy, PR/comms, supply chain…) are registry entries.

## Moat

Lens **depth** (the cyber lens is a working GRC tool, not a summary), **event threads** (a citable
causal graph across stories no aggregator builds), origin-axis coverage balance, and the
evaluation harness that gates quality (relevance/classification/groundedness/thread accuracy
scored in Langfuse on every prompt change).
