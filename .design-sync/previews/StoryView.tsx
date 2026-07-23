import { StoryView } from "prism-web";

// The full story page: header badges, hero-less variant, Affected + Coverage
// strips, lens switcher with a cached brief, Both Sides, thread, impacts,
// sources with funding chips, and the Ask panel.
const event = {
  id: "demo-1",
  title: "Tanker operators suspend Black Sea routes citing drone-strike risk",
  summary:
    "Major tanker operators halted Black Sea transits after drone strikes damaged 17 vessels, disrupting a corridor that carries roughly two million barrels of crude a day.",
  sector: "business",
  subsector: "trade",
  image_url: null,
  regions: ["UA", "RU", "TR"],
  occurred_at: "2026-07-13",
  last_updated_at: "2026-07-13T14:00:00Z",
  lens_briefs: {
    reader:
      "Shipping companies have stopped sending tankers through the Black Sea after drone attacks hit 17 vessels. The pause chokes a major oil export route, and insurers are already repricing the risk — expect knock-on effects at the pump and pressure for a naval escort arrangement.",
    markets:
      "A two-million-barrel-per-day corridor going offline is a supply shock: expect Brent risk premia, wider tanker rates, and pressure on Russian export names. Watch insurers with Black Sea marine books and energy importers with spot exposure.",
  },
  available_lenses: ["reader", "markets"],
  coverage: {
    origins: { GB: 2, IN: 1, RU: 1, QA: 1 },
    unknown: 0,
    single_origin: false,
  },
  entities: [
    { name: "International Maritime Organization", entity_type: "organization", role: "affected" },
    { name: "Sovcomflot", entity_type: "organization", role: "affected" },
    { name: "Lloyd's of London", entity_type: "organization", role: "affected" },
  ],
  thread: {
    upstream: [
      {
        event_id: "a1",
        title: "Ukraine strikes 17 Russian oil tankers in Black Sea drone attack",
        sector: "politics",
        occurred_at: "2026-07-12T06:00:00Z",
        relation: "leads_to",
        rationale: "The strikes triggered the route suspension covered here.",
        confidence: 0.85,
        image_url: null,
      },
    ],
    downstream: [
      {
        event_id: "b2",
        title: "Oil prices surge 8% as Black Sea shipping halts",
        sector: "finance",
        occurred_at: "2026-07-13T09:30:00Z",
        relation: "leads_to",
        rationale: "Brent jumped after operators suspended Black Sea routes.",
        confidence: 0.8,
        image_url: null,
      },
    ],
  },
  projection: {
    event_type: "supply_disruption",
    source_count: 5,
    cyber: null,
    finance: {
      tickers: ["BP", "SHEL"],
      sector: "energy",
      catalyst: "supply_disruption",
      price_impact: { direction: "up", magnitude: "moderate", confidence: 0.7 },
    },
  },
  sources: [
    {
      article_id: "s1",
      source_name: "The Guardian World",
      source_slug: "guardian_world",
      url: "https://example.org/guardian",
      title: "Tanker giants pause Black Sea transits after drone strikes",
      published_at: "2026-07-13T10:00:00Z",
      stance: "neutral",
      funding: null,
    },
    {
      article_id: "s2",
      source_name: "TASS",
      source_slug: "tass",
      url: "https://example.org/tass",
      title: "Russia condemns attacks on civilian shipping",
      published_at: "2026-07-13T11:00:00Z",
      stance: "critical",
      funding: "state",
    },
    {
      article_id: "s3",
      source_name: "The Hindu",
      source_slug: "thehindu",
      url: "https://example.org/hindu",
      title: "Indian refiners assess crude sourcing risk as Black Sea route closes",
      published_at: "2026-07-13T12:00:00Z",
      stance: "neutral",
      funding: null,
    },
  ],
  perspectives: [
    {
      label: "Western wire framing",
      stance: "neutral",
      origin_country: "GB",
      summary: "Coverage centers the supply disruption and insurance fallout.",
      article_ids: ["s1"],
    },
    {
      label: "Russian state framing",
      stance: "critical",
      origin_country: "RU",
      summary: "Coverage frames the strikes as attacks on civilian infrastructure.",
      article_ids: ["s2"],
    },
  ],
  impacts: [
    {
      id: "i1",
      entity_name: "Crude oil markets",
      effect: "supply_risk_premium",
      direction: "negative",
      horizon: "days",
      confidence: 0.8,
      parent_impact_id: null,
    },
    {
      id: "i2",
      entity_name: "Airlines",
      effect: "fuel_cost_increase",
      direction: "negative",
      horizon: "weeks",
      confidence: 0.6,
      parent_impact_id: "i1",
    },
  ],
};

export const FullStory = () => (
  <div style={{ maxWidth: 760, padding: 16 }}>
    <StoryView event={event as never} />
  </div>
);
