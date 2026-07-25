# Parse documentation

Organized by the [Diataxis](https://diataxis.fr) framework — four kinds of docs,
each for a reader in a different mode. New here? Start with the **Tutorial**.

## 🎓 Tutorial — learning-oriented
Start here if you've never run Parse.
- [**Run Parse locally and flip a lens**](./TUTORIAL.md) — zero to a working
  pipeline and your first lens flip.

## 🔧 How-to — task-oriented
Recipes for a specific goal (assumes basic familiarity).
- [**How-to guides**](./HOWTO.md) — add a source / lens / language, trigger
  ingestion, inspect prod, run the tests.
- [Deployment](./DEPLOYMENT.md) — Railway (backend + Langfuse) + Vercel (web),
  gated backend approval.
- [Local development & observability](./LOCAL_DEV.md) — infra + Langfuse setup.

## 📖 Reference — information-oriented
Complete, factual, code-accurate.
- [**HTTP API**](./API.md) — every `/api/v1` endpoint, params, and response shape.
- [Database schema](./DB-SCHEMA.md) — tables, keys, relationships, stream topics.
- [Enrichment schema & role lenses](./ENRICHMENT-SCHEMA.md) — the extraction schema
  every article produces.

## 💡 Explanation — understanding-oriented
Why the design is what it is.
- [**How stories form and stay coherent**](./STORY-GRAPH.md) — clustering, the
  story-timeline graph (IDF weighting, roundup exclusion, embedding coherence),
  trending, and lens briefs. The product's crux (current implementation).
- [**Storyline graph — design proposal**](./STORYLINE-DESIGN.md) — the three-layer
  redesign (events → stories → branches): Leiden communities, a coherence metric, and
  the root→branch→sub-branch tree. Grounded in the metro-maps / event-evolution
  literature. Supersedes the on-read graph when staged in.
- [Architecture](./ARCHITECTURE.md) — streaming-first pipeline, phases, tech stack.
- [Ingestion & classification](./INGESTION-CLASSIFICATION.md) — collection, the
  relevance gate, routing.
- [Data sources](./DATA-SOURCES.md) — the hybrid ingestion strategy and catalog.
- [The per-story agent](./AGENT.md) — grounded, cited, refusing Q&A.

## 🧭 Product & strategy
Not Diataxis, but where the "what and why for the business" lives.
- [Product brief](./PRODUCT-BRIEF.md) · [Product placement](./PRODUCT.md) — problem,
  promise, positioning.
- [Personas](./PERSONAS.md) — the role-driven personalization model.
- [Market research](./MARKET-RESEARCH.md) — market, competitors, the gap.
- [Roadmap](./ROADMAP.md) — phasing and milestones.
- [`../BLUEPRINT.md`](../BLUEPRINT.md) — one-page strategy.
- [`../DESIGN.md`](../DESIGN.md) — the design system (monochrome chrome, the lens
  flip, the three type voices).

---

### Reading paths
- **New contributor** → Tutorial → Architecture → STORY-GRAPH → HOWTO.
- **Front-end / integrator** → API → STORY-GRAPH (§ trending, § story timeline) → DESIGN.
- **Operator / on-call** → DEPLOYMENT → HOWTO (trigger ingestion, inspect prod).
- **Product / strategy** → PRODUCT-BRIEF → PERSONAS → MARKET-RESEARCH → ROADMAP.
