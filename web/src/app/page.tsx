import Link from "next/link";
import { LensDemo } from "@/components/LensDemo";
import { Reveal } from "@/components/Reveal";

const PERSONAS = [
  {
    key: "general",
    name: "For everyone staying informed",
    color: "var(--lens-general)",
    bg: "var(--lens-general-bg)",
    points: [
      "World news clustered into single stories — not fifty duplicate headlines",
      "Both sides of every contested story, grouped by stance and origin",
      "What happens next: the consequence graph behind each event",
      "Ask anything — answers cite the story's own sources or say \"the sources don't cover that\"",
    ],
  },
  {
    key: "cyber",
    name: "For cybersecurity & GRC",
    color: "var(--lens-cyber)",
    bg: "var(--lens-cyber-bg)",
    points: [
      "CVEs with CVSS, exploitation status, and affected products — minutes after disclosure",
      "Every story mapped to your controls: NIST 800-53, CIS",
      "World events read as threat intelligence: who's exposed, what to check",
      "From a new CVE to \"does this affect me and what do I do\" in under a minute",
    ],
  },
  {
    key: "finance",
    name: "For markets & trading",
    color: "var(--lens-finance)",
    bg: "var(--lens-finance-bg)",
    points: [
      "Tickers, sectors, and catalysts extracted from every market-moving story",
      "Evidence-based price-impact reads with confidence, never hype",
      "Second-order effects: what a breach, a war, a ruling does to the market around it",
      "The same world news everyone reads — priced through your lens",
    ],
  },
];

const TRUST = [
  {
    title: "Field-level provenance",
    body: "Every extracted value — a CVSS score, a ticker, a claim — keeps a link to the exact source that evidenced it.",
  },
  {
    title: "An agent that refuses to guess",
    body: "Ask anything about a story. Answers cite the story's own sources; when the sources don't cover it, the agent says so instead of inventing.",
  },
  {
    title: "Both sides, by design",
    body: "Sources are grouped by stance and country of origin, so you see how each side frames the same event — before deciding what to believe.",
  },
];

export default function LandingPage() {
  return (
    <div className="space-y-24 pb-12">
      {/* ── Hero ─────────────────────────────────────────────────── */}
      <section className="pt-10 text-center sm:pt-16">
        <p
          className="mb-4 text-xs font-semibold uppercase tracking-[0.3em]"
          style={{ color: "var(--ink-faint)" }}
        >
          Role-aware AI news intelligence
        </p>
        <h1
          className="mx-auto max-w-3xl text-5xl font-semibold leading-[1.05] tracking-tight sm:text-7xl"
          style={{ fontFamily: "var(--font-display), serif" }}
        >
          One event.
          <br />
          <span className="spectrum-text">Every angle.</span>
        </h1>

        {/* Refraction figure */}
        <div className="mx-auto mt-10 max-w-xl" aria-hidden>
          <svg viewBox="0 0 560 150" className="w-full">
            <defs>
              <linearGradient id="beamW" x1="0" y1="0" x2="1" y2="0">
                <stop offset="0%" stopColor="currentColor" stopOpacity="0" />
                <stop offset="100%" stopColor="currentColor" stopOpacity="0.9" />
              </linearGradient>
            </defs>
            <line x1="10" y1="75" x2="225" y2="75" stroke="url(#beamW)" strokeWidth="2.5" className="beam-in" />
            <path
              d="M258 40 L292 110 L224 110 Z"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinejoin="round"
              className="prism-glow"
            />
            <line x1="290" y1="80" x2="550" y2="28" stroke="#f59e0b" strokeWidth="2.5" className="beam-out" opacity="0.9" />
            <line x1="290" y1="86" x2="550" y2="86" stroke="#06b6d4" strokeWidth="2.5" className="beam-out" opacity="0.9" />
            <line x1="290" y1="92" x2="550" y2="140" stroke="#8b5cf6" strokeWidth="2.5" className="beam-out" opacity="0.9" />
          </svg>
        </div>

        <p className="mx-auto mt-8 max-w-2xl text-lg leading-relaxed" style={{ color: "var(--ink-muted)" }}>
          Prism clusters worldwide coverage into single events — then reads each one through
          <em> your</em> professional lens. A war is a humanitarian story, a cyber-threat forecast,
          and a market catalyst at once. Switch the lens and watch the same news change meaning.
        </p>
        <div className="mt-9 flex flex-wrap items-center justify-center gap-3">
          <Link
            href="/onboarding"
            className="rounded-full px-7 py-3 text-sm font-semibold transition hover:opacity-85"
            style={{ background: "var(--ink)", color: "var(--bg)" }}
          >
            Get your feed
          </Link>
          <Link
            href="/feed"
            className="rounded-full border px-7 py-3 text-sm font-semibold transition hover:opacity-70"
            style={{ borderColor: "var(--line-strong)" }}
          >
            Browse the news
          </Link>
        </div>
      </section>

      {/* ── The moment: live lens demo ───────────────────────────── */}
      <Reveal as="section">
        <div className="mx-auto max-w-2xl text-center">
          <h2 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            Same story. Different stakes.
          </h2>
          <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
            Flip the lens on a real event and see what changes.
          </p>
        </div>
        <div className="mx-auto mt-8 max-w-2xl">
          <LensDemo />
        </div>
      </Reveal>

      {/* ── Personas ─────────────────────────────────────────────── */}
      <section>
        <Reveal>
          <h2
            className="text-center text-3xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display), serif" }}
          >
            Built for how you read the world
          </h2>
        </Reveal>
        <div className="mt-10 grid gap-5 lg:grid-cols-3">
          {PERSONAS.map((persona) => (
            <Reveal key={persona.key}>
              <div
                className="card-hover h-full rounded-2xl border p-6"
                style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
              >
                <div className="mb-4 h-1 w-10 rounded-full" style={{ background: persona.color }} aria-hidden />
                <h3 className="text-lg font-semibold">{persona.name}</h3>
                <ul className="mt-4 space-y-3 text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
                  {persona.points.map((point) => (
                    <li key={point} className="flex gap-2.5">
                      <span aria-hidden style={{ color: persona.color }}>◆</span>
                      <span>{point}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </Reveal>
          ))}
        </div>
        <Reveal className="mt-6 text-center">
          <p className="text-sm" style={{ color: "var(--ink-muted)" }}>
            New roles are lenses on the same backbone — not new products.
          </p>
        </Reveal>
      </section>

      {/* ── How it works ─────────────────────────────────────────── */}
      <Reveal as="section">
        <div
          className="rounded-3xl border px-6 py-10 sm:px-12"
          style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
        >
          <h2
            className="text-center text-3xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display), serif" }}
          >
            One pipeline, every perspective
          </h2>
          <div className="mx-auto mt-6 max-w-2xl space-y-4 text-[15px] leading-relaxed" style={{ color: "var(--ink-muted)" }}>
            <p>
              Prism continuously ingests worldwide news and authoritative feeds (NVD, CISA KEV),
              gates out noise and promotion, extracts typed facts with field-level provenance, and
              merges the many reports of one real event into a single canonical story.
            </p>
            <p>
              Each story then carries a neutral core — summary, sources, both-sides perspectives,
              an impact graph — plus <strong style={{ color: "var(--ink)" }}>lens briefs</strong>:
              short written reads of what the event means for security teams, for markets, and for
              anyone keeping up. Your role picks the default. Curiosity picks the rest.
            </p>
          </div>
        </div>
      </Reveal>

      {/* ── Trust ────────────────────────────────────────────────── */}
      <section>
        <Reveal>
          <h2
            className="text-center text-3xl font-semibold tracking-tight"
            style={{ fontFamily: "var(--font-display), serif" }}
          >
            Trust what you read — because you can check it
          </h2>
        </Reveal>
        <div className="mt-10 grid gap-5 sm:grid-cols-3">
          {TRUST.map((item) => (
            <Reveal key={item.title}>
              <div className="h-full rounded-2xl border p-6" style={{ borderColor: "var(--line)" }}>
                <h3 className="font-semibold">{item.title}</h3>
                <p className="mt-2 text-sm leading-relaxed" style={{ color: "var(--ink-muted)" }}>
                  {item.body}
                </p>
              </div>
            </Reveal>
          ))}
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────── */}
      <Reveal as="section">
        <div className="relative overflow-hidden rounded-3xl border p-10 text-center" style={{ borderColor: "var(--line)" }}>
          <div className="spectrum-bar absolute inset-x-0 top-0 h-[3px]" aria-hidden />
          <h2 className="text-3xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            Pick your lens. Keep the whole spectrum.
          </h2>
          <p className="mx-auto mt-3 max-w-md text-sm" style={{ color: "var(--ink-muted)" }}>
            Free while we build. No account needed — your lens lives in your browser.
          </p>
          <Link
            href="/onboarding"
            className="mt-7 inline-block rounded-full px-8 py-3 text-sm font-semibold transition hover:opacity-85"
            style={{ background: "var(--ink)", color: "var(--bg)" }}
          >
            Choose your lens →
          </Link>
        </div>
      </Reveal>
    </div>
  );
}
