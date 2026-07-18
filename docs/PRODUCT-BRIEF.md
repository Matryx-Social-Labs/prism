# Product Brief

## Problem
People do not trust the news and cannot easily see the full picture of a story. Coverage is
one-sided or fragmented, the consequences of an event are rarely spelled out, and a curious reader
has nowhere to ask a follow-up question and get a sourced answer. Professionals have the same
problem with higher stakes: a security engineer needs to know within minutes whether a new
vulnerability affects their stack and what to do about it, not read ten articles to find out.

## Product
Prism is a role-aware AI news intelligence platform **for everyone** — professionals and general
readers alike. A user states how they read the world once (a job role, or simply "keep me
informed"), and Prism assembles a feed tailored to them. Every story is delivered with the same
depth regardless of sector, and — the differentiator — every story can be read through **any
lens**: a war is a humanitarian story for a reader, a threat forecast for a security team, and a
market catalyst for a trader. Switching the lens on a story swaps its written brief, its
structured fields, and the agent's suggested questions.

### The four-part promise, per story
0. **Lens briefs.** A written read of the event through each professional lens — what it means
   for defenders (who is exposed, what to check), for markets (sectors, tickers, likely
   direction), and for anyone staying informed. The user's lens leads; every other lens is one
   tap away.
1. **Both Sides.** The story's sources are grouped by stance and by country or party of origin, so
   the reader sees how each side frames the same event. For an international dispute this means
   pulling and translating sources from the parties involved, not only domestic outlets.
2. **So What.** An impact and consequence view: the organizations, companies, and people affected,
   and the likely second-order outcomes, presented as a readable narrative backed by a graph.
3. **Ask.** A grounded agent scoped to that one story, answering follow-up questions from the
   event's clustered sources with citations.

### Personalization
The core of the product is the personalization layer:
`user profile (role plus interests)` gives a `role lens` (which extra fields and framing apply)
and a `relevance and ranking model` (what to surface and in what order), producing a
`personalized feed` where each story still carries the full depth.

## Positioning
Not another aggregator that shows more headlines faster. Prism is the product that shows you every
side of a story, tells you what it means and what happens next, lets you ask, and does all of this
shaped to your role — while letting you borrow anyone else's lens on demand. One-line pitch:
**"One story. Every perspective."** Role-specific pitch for the deepest lens: the security and GRC news
feed that tells you what a story means for your controls, from both sides, with a briefing you can
question.

## Target users
See [PERSONAS.md](./PERSONAS.md). The first release is built for cybersecurity and GRC
professionals; later roles are added as lenses. Personas are open-ended, not a fixed set.

## Business model
Prosumer subscription for individual professionals in the beachhead. Later expansions can add
finance and general-reader tiers and, eventually, B2B team seats. Willingness to pay for consumer
news is plateauing, which is another reason to lead with a professional role that has budget.

## What good looks like (early success signals)
- Clustering quality: related reports of one event land in one cluster with few false merges.
- Perspective coverage: for contested stories, the product surfaces genuinely distinct framings,
  not near-duplicates.
- Agent groundedness: answers cite the story's own sources and do not assert beyond them.
- Beachhead value: a security or GRC user can go from a new CVE to "does this affect me and what do
  I do" in under a minute.
- Retention: professionals return daily, because the feed saves them time they would otherwise
  spend triaging sources by hand.

## Non-goals for v1
- No general "all news for everyone" launch. One role, done deeply.
- No real-time trading fast-lane yet (that is Phase 2, the finance lens).
- No proprietary global scraping estate on day one; ingestion is hybrid.
