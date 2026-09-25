# Roadmap

> **Historical phasing (2026-07-27).** Milestones below predate the India-only reset, the removal of GDELT and the paid launch plan. For what shipped, read [`../CHANGELOG.md`](../CHANGELOG.md).

The strategy is a vertical beachhead first, then horizontal expansion by adding role lenses on the
same backbone. This keeps scope tight (the lesson from Artifact's failure) while building toward the
full multi-role vision.

## Phase 0 — Blueprint (done)
Research report, competitive analysis, personas, architecture, schema, and this directory. See the
top-level [BLUEPRINT.md](../BLUEPRINT.md) and [docs/MARKET-RESEARCH.md](./MARKET-RESEARCH.md).

## Phase 1 — Cybersecurity and GRC beachhead
Ship the full experience for one role.

**Milestone 1.1 — Thin vertical slice. ✅ (July 2026)** One end-to-end path: ingest NVD/CVE and
CISA KEV plus GDELT and security RSS, run the relevance gate, enrich with the shared schema and
the cyber lens, cluster into events, and serve a single event view with sources.

**Milestone 1.2 — The three-part story view. ✅ (July 2026)** Perspective grouping (both sides),
the impact and control-mapping view (so what for your controls), and the per-story agent (ask),
with citations and refusal, verified against live multi-source events.

**Milestone 1.3 — Personalization. ◐ in progress** Done: onboarding captures the role and selects
a lens (localStorage profile); a declarative lens registry (`common/lenses.py`) drives per-lens
feed ranking and suggested questions (ranking only — a lens never scopes the feed by sector);
landing page + lens switcher. Remaining:
real accounts, follow rules for specific vendors/products/CVEs/tickers, and alerts.

**Milestone 1.4 — Prosumer subscription.** Accounts, plans, and billing for individual security and
GRC professionals. Groundedness and extraction evaluation gates in place before opening access
(eval harness exists in `evals/`; gates not yet enforced).

Exit criteria: a security or GRC user can go from a new CVE to "does this affect me and what do I
do" in under a minute, with sources and a questionable agent, and returns daily.

## Phase 2 — Finance and trader lens ◐ started early (validating the multi-role thesis)
Done: the finance lens rides the same backbone — classifier tags `finance_trader`, extraction
fills tickers/sector/catalyst/price-impact, correlation merges them into the event projection,
the feed ranks by price-impact under the finance lens, and the story view shows the market read.
GDELT runs a finance query alongside the cyber one. Remaining: dedicated finance feeds
(Marketaux; a real-time catalyst feed if needed) and the low-latency fast-lane delivery over the
streaming transport.

## Phase 3 pull-forward — the multi-lens platform for everyone ✅ (July 2026, founder decision)
The general reader was promoted from Phase 3 to a first-class persona, and the product
repositioned from "for cybersecurity professionals" to **role-aware news intelligence for
everyone** ("One story. Every perspective."):
- **World-news ingestion**: BBC World, Al Jazeera English, Guardian World RSS (origin-diverse
  outlets feed Both-Sides grouping) + a GDELT world query — the general feed now carries real
  world news, not only professional stories.
- **Lens briefs** (the core multi-lens feature): every event carries written per-lens analysis —
  general always; the story's primary lens generated at pipeline time; any other lens generated
  on demand and cached. A war story exposes a cyber read (who is exposed, what to check) and a
  market read (sectors, tickers, direction) on request; CVE records get zero-LLM template briefs.
- **Web**: spectrum-brand redesign (adaptive dark/light), landing page with a live lens-switch
  demo, story pages with in-place lens switching.
Beachhead depth is unchanged — the cyber/GRC lens remains the deepest; lens depth is the moat,
the multi-lens experience is the product.

## Phase 3 pull-forward, part 2 ✅ (July 2026) — India-first personalization release
- **Sub-domain taxonomy** (`common/taxonomy.py`): 10 sectors × sub-domains (sports → cricket…,
  technology → AI…); classifier emits validated subsectors; single-topic feeds classify
  deterministically (zero LLM).
- **15 new sources** across 11 origin countries incl. 7 Indian outlets and labeled state media
  (TASS, CGTN, Press TV, Anadolu) + public broadcasters (DW, France 24); GDELT India query.
- **Personalized feed without accounts**: `interests=sector[:subsector]`, `region=`,
  `sort=latest|top` (latest default); 3-step onboarding (region → lens → interests) in
  localStorage; All/India/World scoping.
- **Thumbnails** end-to-end (RSS media tags, GDELT socialimage, og:image at fulltext fetch).
- **Conditional lenses**: stories offer only lenses with a genuine read.
- **Coverage-origin balance**: per-story origin distribution + single-origin blindspot flag;
  outlet funding labels.
- **Event threads**: `event_links` graph (leads_to/related, negative-cached rejections), one
  batched LLM confirm per new candidate set, ThreadRail UI (what led here / what followed).
- **Web**: real 3D glass prism hero (react-three-fiber, lazy, reduced-motion/no-WebGL poster
  fallback), thumbnails on cards, funding chips.
- Next gates unchanged: auth + server-side profiles (1.4), follows/alerts, mobile (Expo),
  Marketaux fast-lane.

## Next up (planned July 2026) — priority order
1. **Accounts + synced profiles** (finishes 1.4): lightweight magic-link auth (Auth.js),
   `user_profiles` table, server-side interests/lens/region sync. localStorage remains the
   guest mode; accounts unlock cross-device continuity and the mobile app.
2. **Follows & alerts**: follow entities, sectors, and threads; digest email + web push when a
   followed thread gains a downstream event ("what followed" notifications — the event-links
   graph makes this differentiated).
3. **Search**: Postgres full-text + pgvector semantic search over events; search bar in the feed.
4. **Lens platform**: registry fully server-driven end-to-end (the web now renders whatever
   /api/v1/lenses returns, with styling fallbacks — done July 2026); add a "request a lens"
   affordance; pick the next lens from usage signals (candidates: Policy/Legal, Health).
5. **Mobile (Expo React Native)** on the same /api/v1; extract the typed client into
   packages/api-client first.
6. **Quality & ops**: thread-direction eval 0.75 → ≥0.9 (prompt iteration on thread-link);
   extraction field-agreement evals; Langfuse cost dashboard per stage; source expansion —
   fix/replace Press TV, add African + Latin American origins.
7. **Sharing & SEO**: public story pages with OG images, sitemap, per-story canonical URLs.

## Phase 3 — Horizontal expansion
Open personalization to general roles and sectors, add a prosumer graph and public API, and later
introduce B2B team seats for security, PR, and risk teams. Cross-national both-sides framing widens
from the beachhead's priority languages to broader coverage.

## Cross-cutting, from the start
- **Evaluation harness.** Labeled gold sets for the relevance gate, classification, enrichment, and
  agent groundedness, ported from EduThreat. Do not scale collection before these exist.
- **Provenance and reproducibility.** Field-level provenance on every value, so served numbers and
  agent answers are auditable.
- **Cost discipline.** Incremental collection with watermarks, and expensive LLM work only past the
  relevance gate.

## Open decisions to settle early
- Final product name (working codename "Prism").
- Streaming backbone (Kafka/Redpanda vs NATS) and search store.
- First news-event API to license, and the initial region and language priority.
- Whether Phase 1 also seeds a second research paper, which would raise the measurement rigor baked
  into the pipeline from day one.
