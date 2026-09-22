# Plan: the subject tree — a deeper, decidable classification, and what it buys the product

**Source**: conversational (`/ecc:plan`, 2026-09-22)
**Complexity**: Large — vision + architecture first, then four buildable phases
**Status**: awaiting decisions D7–D11 below. No code until they are answered.

---

## 1. What you asked for, restated

A tree: root (all news) → high-level subject (sports, politics, business…) → finer
(cricket, basketball…) → finer still, as deep as each branch deserves, so the product
can do **realistic analysis** — the example given: under business → stocks, a story
about a company relates to a **ticker**, and to the other news around it, feeding the
story/arc features and a "where, what, how" reading.

## 2. What the corpus says before we design anything

Measured on production, 30 days to 2026-09-22 (9,984 events):

| Finding | Number | What it means for the design |
|---|---|---|
| Events with a sub-sector | 71 % | Level 2 is only three-quarters populated today |
| `other` or no sector | **22 %** | The biggest bucket in the product is the one with no name |
| Biggest sports bucket is `other_sports` | 258 | The catch-all beats every named sport |
| Events carrying a validated ticker | 321 (3 %) | The ticker link is real but rare |
| Sports events naming cricket terms | 168 | A cricket node would genuinely fill |

**What is actually inside the buckets** (sampled at random, verbatim):

- `other` — *"Girl scream 'I won't die', accused flees after running her over"*,
  *"Massive fire breaks out at furniture showroom"*, *"Surendra Koli found dead"*,
  *"Toilets to be built at Mysore Zoo… for 7.3 million rupees"*.
  **This is not a taxonomy failure. It is crime, accidents and civic works — the most
  common kind of Indian local news — with no branch to live in.**
- `business/corporate` — *"13 bus stations in Telangana to turn integrated transit
  hubs"*, *"New Dairy Building Inaugurated"*, *"IIM Visakhapatnam opens admissions"*,
  *"Expired infant food seized"*, *"Oil India plans ₹15,000 crore deepwater
  exploration"*, *"Mahindra to launch new Thar facelift"*.
  **Two of six are corporate. Level 2 is already a dumping ground.**

### The conclusion that should shape everything

**Depth is worthless under a wrong parent.** Adding `sports → cricket → IPL` while
`business/corporate` holds a dairy building and 22 % of the corpus sits in a bucket
called "other" multiplies an existing error instead of fixing it. The first move is
not *deeper*; it is **wider at the top and decidable at every step**.

## 3. The architecture: one tree for navigation, facets for analysis

A strict single tree cannot hold real news. *"Oil India plans ₹15,000 crore deepwater
exploration"* is simultaneously energy, corporate investment, Odisha, a state-owned
company, and (if listed) a ticker. Forcing one path throws away four of five.

So: **a primary path in a tree, plus orthogonal facets.** They answer different
questions and only the first is navigation.

```
SUBJECT TREE (one primary path per story — what a reader browses)
root
├── politics ──────┬── elections ──── assembly | general | local-body
│                  ├── governance ─── policy | appointments | parliament
│                  ├── courts & law ─ judgments | investigations | tribunals
│                  └── diplomacy ──── bilateral | multilateral | conflict
├── business & markets ─┬── companies ── results | deals | leadership | products
│                       ├── markets ──── equities | commodities | currency | crypto
│                       ├── economy ──── inflation | trade | jobs | budget
│                       └── sectors ──── energy | auto | banking | pharma | IT …
├── sports ─────┬── cricket ──── international | IPL | domestic
│               ├── football | kabaddi | athletics | chess | motorsport …
│               └── (a node only exists once it fills — see the floor below)
├── tech & cyber ─┬── AI | software | hardware | telecom
│                 └── security ── vulnerabilities | breaches | malware | policy
├── health & science ─┬── public health | medicine | outbreaks
│                     └── space | climate | research
├── entertainment ──── film | music | television | celebrity
└── civic & safety ◀── NEW ─┬── crime ──── violent | property | cyber-enabled
    (today's "other", 22%)  ├── accidents & disasters
                            ├── civic works & local government
                            └── obituaries & notices

FACETS (orthogonal, multi-valued — what analysis joins on)
  event-type   announcement · decision · result · incident · investigation · launch …
  actors       → entities (already extracted, already has pages) 
  instrument   → securities (ISIN-keyed, validated) — the ticker link
  geography    → regions (country + IN state, already extracted)
  lens-fitness → which professional reading this story earns (already exists)
```

**Why facets are the answer to your ticker example.** "Business → stocks → this story
is about RELIANCE" is not a deeper tree node — RELIANCE is an *entity* that resolves to
a *security*. The tree gets the story to `business & markets → companies → results`;
the facet says *which company*, and the securities master says *which ISIN*. Analysis
("every story about this ticker", "what moved this sector this week") is then a join,
not a taxonomy lookup. The entity pages shipped today (`/entity/<slug>`, 5,779 live)
are already half of this.

### Three rules that keep the tree honest

1. **A node must be decidable by its siblings alone.** Classification asks one
   question per level, with the parent fixed. Jev's `choice` is exactly this shape:
   ≤255 options, one pass, calibrated. A 200-way flat choice would be worse at every
   level.
2. **A node must earn its existence: ≥ 30 stories a month, or it does not ship.**
   An empty sector page is a promise the product breaks. `other_sports` stays as a
   real node (258/month) rather than a fiction of twelve empty sports.
3. **Every node is a URL and a feed.** `/subject/sports/cricket` must return a full
   page of stories, or the node should not exist. This is also what earns the SEO
   long tail — the same argument that made entity pages worth building.

## 4. What this unlocks (why it is worth doing)

| Capability | Needs | Why it is not possible today |
|---|---|---|
| "Every story about this ticker, this month" | facet: instrument | tickers exist (3 %) but nothing joins them to a subject |
| "What moved banking this week" | tree node + event-type facet | `finance/banking` is one flat bucket of 139 |
| Crime & safety as a readable beat (22 % of corpus) | new branch | "other" is invisible by decision D3 |
| A reader following *cricket*, not *sports* | depth + interests contract | interests are `sector` or `sector:sub` only |
| Sector pages that rank (SEO long tail) | node = URL = feed | six pages today; ~60 defensible ones after |
| Story arcs scoped to a subject | tree node on the story, not just the event | arcs group by embedding + cast only |

## 5. Decisions I need from you (D7–D11)

These are product decisions, not technical ones. I have a recommendation for each.

**D7 — Does the nav stay six?** D3 fixed six first-class sectors. A `civic & safety`
branch makes seven, or crime lives under an existing one.
*Recommendation: seven.* 22 % of the corpus has no home, and "crime & safety" is a beat
a reader recognises. The alternative is leaving a fifth of the product unreachable.

**D8 — How deep, and does it vary by branch?** A uniform three levels is tidy and
wrong: cricket deserves four, entertainment probably two.
*Recommendation: depth varies; the ≥30-stories-a-month floor decides, re-checked monthly.*

**D9 — Does a story get one path or many?** One primary path (navigation, breadcrumbs,
"this story is in") plus facets; or genuine multi-label.
*Recommendation: one primary path + facets.* Multi-label breaks breadcrumbs, dedupe and
"what is in this section", and facets already carry the other dimensions.

**D10 — Is the taxonomy derived or authored?** Invented trees have empty nodes; derived
trees drift with the corpus.
*Recommendation: authored spine, derived depth.* You and I fix levels 1–2 by editorial
judgement; levels 3+ are proposed from what the corpus actually contains (cluster the
bucket, name the clusters, keep the nodes that clear the floor) and ratified by you.

**D11 — What happens to the 14k existing events?** Re-classifying them costs about
**$0.70 total on Jev** (14,183 × ~$0.00005) and a few hours of wall time.
*Recommendation: full backfill.* A tree that only applies to new stories makes every
archive page and every analysis half-empty.

## 6. Phases (after D7–D11)

**Phase 0 — the taxonomy becomes data, not a Python dict** (S)
`common/taxonomy.py` is a flat dict read by ten modules. Introduce a `subjects` table
(id, parent_id, slug, label, depth, status) + a typed accessor with the same API, so
the tree can change without a deploy and a node can be retired without breaking a URL.
Mirrors: `common/regions.py` (table-shaped vocabulary), `db/versions/*` (migration
style). Old `sector`/`subsector` columns stay and are derived from the path for
backward compatibility — nothing downstream breaks on day one.

**Phase 1 — the spine, and crime gets a home** (M)
Levels 1–2 authored with you, including the new branch. Classification asks Jev one
`choice` per level (parent fixed). Measure against a hand-labelled sample per branch
before anything serves. This alone fixes the 22 % and the `business/corporate` dumping
ground — the largest quality win available.

**Phase 2 — depth where the corpus earns it** (M)
Propose level 3+ per branch from real clusters; you ratify; nodes that clear the floor
ship. Cricket, equities, crime types first (they have the volume).

**Phase 3 — facets and the joins that make analysis** (M)
Event-type facet; entity→security resolution so a company story carries its ISIN;
`/subject/<path>` pages and `/ticker/<symbol>` pages; interests contract extended from
`sector:sub` to a path. This is where your stock example becomes a feature.

**Phase 4 — the analysis surfaces** (L, separate plan)
"What moved this subject this week", ticker timelines, subject-scoped arcs. Planned
separately once the data exists — I will not design surfaces on a taxonomy that has not
been measured yet.

## 7. Risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Deeper tree, same wrong parents | **High** if we skip Phase 1 | Fix levels 1–2 and measure before adding depth |
| Empty nodes make the product look thin | Medium | The ≥30/month floor, re-checked monthly |
| Nav grows past what a phone holds | Medium | Seven at level 1 is the cap; depth lives inside a section |
| Re-classification changes what a reader saw yesterday | Certain | Backfill once, announce it, keep old URLs redirecting |
| Facets become a second taxonomy nobody maintains | Medium | Facets reuse what exists (entities, securities, regions) — only event-type is new |
| Jev is wrong at depth 3 where options are subtle | Medium | Per-branch gold sample before each node ships; fall back to the parent rather than guess |

## 8. What I explicitly do not recommend

- **Not** a 200-node tree authored up front. Nodes without stories are a liability.
- **Not** multi-label as the primary structure — it breaks navigation, and facets do
  the job better.
- **Not** building analysis surfaces (Phase 4) before Phases 1–3 are measured.
- **Not** touching the six-sector nav's *look*: D3 binds the surface; this changes what
  is under it, and adds one branch if you approve D7.

## Acceptance
- [ ] D7–D11 answered
- [ ] Levels 1–2 authored and measured per branch before serving
- [ ] Every shipped node returns a full page of stories
- [ ] Backfill complete; `sector`/`subsector` still derivable for old clients
- [ ] Ticker example works end to end: story → company entity → ISIN → ticker page
