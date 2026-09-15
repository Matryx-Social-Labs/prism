# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

**Primary: the general Indian news reader, on a phone, in the gaps of a day.** They
want to know what happened and, when it matters, to see that a story has more than one
side without doing the work of reading six outlets. They read English first; many also
read Hindi, Kannada, Tamil or Marathi and should not be shown a language they did not
choose. Their first visit is signed-out and often from a shared link or a search result.
(Founder decision 2026-09-15, D1: the general reader leads the first screen.)

**Paid audience, one tap away: professionals whose job depends on the news** —
markets readers (traders, analysts, finance creators) and cyber/GRC readers. They read
the same stories but need a different reading of them: which tickers move, what the
catalyst is, whether a CVE is exploited in the wild. They are not a separate front door;
the stories that earn a professional read say so on the feed, and the read itself is
what they pay for.

**Internal: the founder and a non-technical review team** who need to open the site
once ingestion is on and check, visually, that the pipeline's facts are right — that a
story is one story, that a quote is attributed correctly, that the sources shown are
the sources used. Everyone must be able to see the same page to do this (D2).

## Product Purpose

Prism ingests Indian news across outlets and languages, clusters the coverage into
**canonical stories** (one event, every outlet that reported it), and lets a reader
re-read any story through a **lens** — a role-aware reading of the same facts. Under
each story it shows **who said what**, verbatim and attributed, checked against the
article it came from. Success is a reader who can say "I understand this story, I can
see who is saying what, and I can check it" — and a professional who finds their
reading of it worth paying for.

Tagline: **"One story. Every perspective."** It is a promise about evidence, not tone.

## Positioning

The mechanism a neighbouring product cannot truthfully copy: **verbatim or nothing.**
A claim is displayed only if its exact words are found in the source article; a ticker
is displayed only if a listed security carries it; the story's shape (developments,
branches, span) is counted, never summarised by a model. Ground News shows outlet
bias; Particle and Inshorts summarise. Prism shows the record and lets the lens
re-read it. The **lens flip** — the same story re-typesetting itself for a different
reader — is the memorable thing and the brand.

## Operating Context

- **Corpus:** 42 sources, 6 languages (English, Hindi, Kannada, Tamil, Marathi,
  Telugu). Display is English-first; a reader's chosen languages rank and localise,
  never filter. Ingestion runs on a cadence when enabled (currently off; the corpus
  is frozen at 2026-09-05 until sources are decided).
- **Corpus shape today:** ~1,357 stories in the live window — politics 40%,
  business+finance 18%, sports 9%, health/science/tech/cyber the rest. 22% carry no
  sector. 3% carry a validated ticker. 45% carry at least one verbatim claim.
- **How it is read:** on a phone, mostly signed out, often arriving on a story page
  from a link. Desktop exists for the professional and the review team; extra width
  buys simultaneity (evidence beside the story), never longer lines.
- **The review ritual:** the founder and team open the live site and spot-check
  stories against the pipeline's facts. A shared front page is what makes this possible.
- **Pipeline surfaces the reader meets:** Feed (front page), Story, Sector pages with
  sub-sectors, Trending (story arcs), Market Pulse (a daily markets digest), Search,
  Watchlist (tickers/sectors), You (profile: state, role/lens, interests, languages),
  Onboarding (three steps: where you are, what you do, what you follow), Ask (grounded
  Q&A per story, metered).

## Capabilities and Constraints

**Confirmed capabilities**
- Canonical story clustering with a branch tree (developments · branches · satellites ·
  span), counted not summarised.
- Lens re-read per story: Reader (free), Markets and Cyber (paid; health and policy
  drafted, not served). A locked lens still flips — the reader sees what they are
  missing — and the brief is gated server-side.
- Verbatim, attributed claims per story ("What was said"), free to all readers,
  grouped by speaker, each cited `[n]` to the source list.
- Personalisation contract: state (ISO 3166-2), role/lens, interests (sector or
  sector:sub-sector), languages in preference order. The feed API honours all of them.
- Sector pages with sub-sectors; scope of All / State / National.
- Validated tickers (symbol master of 15,701 securities; zero unvalidated tickers
  stored). No price data yet.
- Ask: grounded per-story Q&A, cites the story's own sources or says it cannot;
  metered (3 per anonymous session, 30/day signed in).

**Decisions that bind the redesign (founder, 2026-09-15)**
- **D1** The general reader leads the first screen; professional depth is one tap away
  and visibly advertised on the stories that earn it.
- **D2** One editorial front page for everyone, a permanent sector nav on every surface,
  and a "For you" tab that appears once a reader has picked interests. Nobody is forced
  through onboarding to read.
- **D3** Six first-class sectors in the nav: **Politics · Business & Markets · Sports ·
  Tech & Cyber · Health & Science · Entertainment.** "Other" is never shown as a
  heading; its stories are reachable through search and the story page. The Markets
  and Cyber *lenses* stay separate from sectors — a lens is a way of reading, not a
  subject.
- Mobile-first, responsive. Desktop is a composition of the same content, not a
  different product.
- The most-corroborated stories lead. Single-source stories do not lead a front page
  whose promise is "every perspective".
- English-first display for a reader with no language preference.

**Undecided (recorded, not invented)**
- Which markets sources to add and when ingestion resumes.
- Whether the LLM "Perspectives" cards on the story page are retired now that verbatim
  claims exist beside them.
- Whether reported (indirect) speech should display as a claim.
- Pricing UI and the payment provider (UPI Autopay via a PSP) — the paywall boundary
  exists; the checkout does not.

## Brand Commitments

- **Name and mark: Prism, and the existing logo — unchanged** (founder, 2026-09-15).
  The mark is a bracketed record holding three rules: one record, three readings.
- **The lens flip is the memorable thing.** Every design decision serves it. It is a
  re-typeset — a scan line and re-ink, ~500ms, collapsing to an instant swap under
  reduced motion — never a crossfade. Body text and layout never move.
- **Chrome is monochrome; colour only ever means a lens is speaking.** Lens hues are
  discrete and semantic: reader amber, cyber cyan, markets violet; reserved sky, rose,
  lime, fuchsia for future lenses. Never gradients as decoration.
- **Three type voices, three jobs:** a display face for storytelling, a UI/body face,
  and a monospace face used only for provenance (timestamps, sources, citations,
  tickers, CVE ids). Whether the current faces (Fraunces, General Sans, IBM Plex Mono)
  survive the redesign is a visual-world decision, not a product one; the three-voice
  rule is the commitment.
- Voice: editorial, direct, factual. Never marketing copy on app surfaces; never
  enumerate lens names in generic copy (the lens set grows).

## Evidence on Hand

- A live production site: readprism.news (Vercel + Railway). Real stories, real sources.
- The story page as it ships today, including "What was said" (c3e5b96) — measured A on
  every binding design rule.
- 1,285 verbatim-verified claims across 755 articles; attribution precision 0.983 on a
  59-claim adjudicated gold set (`tools/gold_claims.py`).
- A 1,147-pair adjudicated story-boundary gold set (`tools/gold_story_pairs.py`).
- A 15,701-row securities master with ISINs.
- Screenshots of every current surface at 1440 and 390:
  `~/.gstack/projects/Matryx-Social-Labs-prism/designs/redesign-20260915/`.
- The evaluation that motivated this redesign: `00-evaluation.md` in the same folder.

**Absences future work must not fabricate:** no testimonials, no customer names, no
user counts, no market price data, no benchmark claims, no press.

## Product Principles

1. **Show the record, not a verdict.** Counted structure, verbatim quotes, named
   sources. The reader judges; Prism makes judging possible.
2. **One page everyone can check.** The front page is shared and editorial so a
   founder, a reviewer and a stranger see the same thing and can point at it.
3. **The subject is one tap away, everywhere.** Six sectors, same nav on every
   surface. A reader never has to know a URL or scroll to find their beat.
4. **The paid reading is advertised by the story that earns it.** A story with a
   markets read says so on the feed; the flip to a locked lens shows what is missing.
5. **Mobile is the product; desktop is the same product with room for evidence.**

## Accessibility & Inclusion

- WCAG AA contrast on body text and UI components (DESIGN.md's ink scale was chosen
  for it); reduced-motion collapses every animation, including the flip.
- Six scripts must render in the body voice without fallback mismatch (Devanagari,
  Kannada, Tamil, Telugu, Latin). Verified for Devanagari and Kannada on the story page.
- Touch targets ≥ 44px on every interactive element on mobile (a 19×16 citation was
  the last miss, fixed in a5b5d96).
