# Personas and the Personalization Model

Personas in Prism are open-ended. A user's job role and interests, captured at onboarding, select
a **role lens** over a shared event backbone. A lens decides which extra fields are extracted,
which framing is shown, and how the feed is ranked for that user. New roles are added by defining a
new lens, not by rebuilding the pipeline.

## The personalization layer
```
user profile (role + interests)
        │
        ├──▶ role lens          → which extra fields, framing, and defaults apply
        └──▶ relevance + ranking → which events to surface, in what order
        │
        ▼
personalized feed (each story delivered with full depth: both sides, cluster, impact, agent)
```

Onboarding captures, at minimum: primary job role, sectors of interest, regions of interest, and
optionally specific entities to follow (companies, vendors, products, tickers, topics). These map
to a profile that drives both the lens and the ranking model.

## Illustrative personas

### 1. Cybersecurity / GRC professional — "Defend and comply" (beachhead)
- **Wants:** fast updates on security incidents and CVEs, with CVSS, affected products and
  versions, exploitation status, and a clear read on what this means for their controls (which
  frameworks and controls it maps to, what to patch or mitigate).
- **Lens adds:** CVE identifiers, CVSS vector and score, affected vendors, products, and version
  ranges, known-exploited status (CISA KEV), and control and framework mapping.
- **Why first:** reuses the EduThreat pipeline and data almost directly, has clear willingness to
  pay, and is friendly to a prosumer subscription.

### 2. Active retail stock trader — "Act fast" (Phase 2)
- **Wants:** real-time, low-latency alerts on market-moving news, ticker and sector tagging,
  sentiment and likely price impact, and a "why is it moving" read.
- **Lens adds:** tickers, sector, sentiment, and a price-impact read, delivered through the
  real-time fast-lane.

### 3. Prosumer analyst / journalist / researcher — "Go deep"
- **Wants:** the event graph, source provenance, cross-national framing, and export or API access.
- **Lens adds:** deeper provenance surfacing and graph and export tools rather than new extraction.

### 4. Casual regional / international reader — "Stay informed"
- **Wants:** a clean daily feed by region and sector, the gist fast, both sides, and the option to
  ask.
- **Lens adds:** lightweight framing; ranking favors breadth and readability over depth.

### 5. (Later, B2B) newsroom / PR / risk, policy, or compliance team — "Monitor"
- **Wants:** entity and topic monitoring, alerts, dashboards, and seats.
- **Lens adds:** saved monitors and team workflows; enterprise pricing.

## Design implication
Because the lens is a declarative add-on over shared extraction, the pipeline does not branch per
role. The shared enrichment produces the common fields for every story, and each active lens
contributes its extra fields and framing. This is what lets Prism start with one role and expand
without a rewrite. The concrete field sets are defined in
[ENRICHMENT-SCHEMA.md](./ENRICHMENT-SCHEMA.md).
