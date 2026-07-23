import Link from "next/link";
import { HeroLensDemo } from "@/components/HeroLensDemo";
import { Reveal } from "@/components/Reveal";

// The three lenses live in the product today (mirrors /api/v1/lenses).
// Rendered as filled chips — a lens IS speaking, so color is allowed.
const ACTIVE_LENSES = [
  { name: "Reader", color: "var(--lens-general)", bg: "var(--lens-general-bg)" },
  { name: "Cyber", color: "var(--lens-cyber)", bg: "var(--lens-cyber-bg)" },
  { name: "Markets", color: "var(--lens-finance)", bg: "var(--lens-finance-bg)" },
];

// Upcoming lenses — shown as dashed outlines, not selectable. Reserved hues
// from DESIGN.md (no token yet; these carry lens identity only).
const UPCOMING_LENSES = [
  { name: "Health", tag: "next", color: "#be123c" },
  { name: "Policy", tag: "next", color: "#0369a1" },
  { name: "Legal", color: "#4d7c0f" },
  { name: "Supply chain", color: "#a21caf" },
  { name: "+ your role", color: "var(--ink-faint)", muted: true },
];

const BOTH_SIDES = [
  {
    label: "Access to medicine won",
    region: "India · Global South",
    body: "Domestic and global-health outlets frame the ruling as a public-health milestone: a drug priced for the few, opened to millions.",
    sources: [{ name: "The Hindu" }, { name: "DW", funding: "Public broadcaster" }],
  },
  {
    label: "Innovation undermined",
    region: "US · EU",
    body: "Industry and financial press frame it as patent erosion that will chill R&D investment in the region — and warn of trade consequences.",
    sources: [{ name: "WSJ" }, { name: "FiercePharma" }],
  },
];

const HOW_STEPS = [
  { n: "01", title: "Cluster", body: "Fifty duplicate headlines about one real event become a single canonical story with every source attached." },
  { n: "02", title: "Balance", body: "Each story's coverage-origin mix is measured. One origin only? It's flagged as a blindspot." },
  { n: "03", title: "Lens", body: "Written briefs re-read the same story for each profession. Lenses are added continuously on the same backbone." },
  { n: "04", title: "Ground", body: "Ask anything. The agent answers from the story's own sources with citations — or refuses, visibly." },
];

// So What — the AI-chip export consequence graph.
const CONSEQUENCES = [
  { glyph: "●", color: "var(--up)", entity: "Domestic data-center builders", effect: "accelerated GPU procurement", horizon: "weeks" },
  { glyph: "↳", color: "var(--up)", entity: "Power utilities near new capacity", effect: "grid-demand contracts reprice", horizon: "months", child: true },
  { glyph: "●", color: "var(--danger)", entity: "Grey-market resellers", effect: "arbitrage window closes", horizon: "immediate" },
  { glyph: "↳", color: "var(--ink-faint)", entity: "Non-allied markets", effect: "domestic accelerator programs gain urgency", horizon: "quarters", child: true },
];

const BLINDSPOTS = [
  {
    tags: ["⚠ One-sided coverage", "Elections"],
    title: "State assembly passes contested electoral-roll revision bill",
    note: "7 sources · all aligned with the ruling party — the opposition's framing hasn't been picked up. Prism pulls it in and shows both.",
  },
  {
    tags: ["⚠ Single-origin", "Trade"],
    title: "Deep-water port expansion approved on strategic shipping lane",
    note: "4 sources · one origin country — the rest of the world's media hasn't picked this up yet.",
  },
];

function Card({ children, className = "", pop = false }: { children: React.ReactNode; className?: string; pop?: boolean }) {
  return (
    <div
      className={`rounded-[18px] border ${className}`}
      style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", boxShadow: pop ? "var(--shadow-card)" : undefined }}
    >
      {children}
    </div>
  );
}

function Eyebrow({ children }: { children: React.ReactNode }) {
  return (
    <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--ink-faint)" }}>
      {children}
    </p>
  );
}

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-[1160px] px-5 sm:px-8 xl:px-10">
      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="grid items-center gap-10 pb-12 pt-12 sm:pt-16 lg:grid-cols-[minmax(0,1fr)_minmax(0,480px)] lg:gap-14 lg:pb-14 lg:pt-[76px]">
        <div>
          <p className="mb-4 text-[11.5px] font-semibold uppercase tracking-[0.3em]" style={{ color: "var(--ink-faint)" }}>
            Role-aware news intelligence
          </p>
          <h1
            className="text-[40px] font-semibold leading-[1.04] tracking-tight sm:text-[56px] lg:text-[68px] lg:leading-[1.02]"
            style={{ fontFamily: "var(--font-display), serif" }}
          >
            One story.
            <br />
            <span className="spectrum-text">Every perspective.</span>
          </h1>
          <p className="mt-5 max-w-[480px] text-[15px] leading-[1.6] sm:text-[17px] sm:leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Prism clusters worldwide coverage into single events, then reads each one through{" "}
            <em>your</em> professional lens — whatever your profession is. Switch the lens and the
            same news changes meaning.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              href="/onboarding"
              className="rounded-full px-7 py-[13px] text-sm font-semibold transition hover:opacity-85"
              style={{ background: "var(--ink)", color: "var(--bg)" }}
            >
              Get your feed
            </Link>
            <Link
              href="/feed"
              className="rounded-full border px-7 py-[13px] text-sm font-semibold transition hover:opacity-70"
              style={{ borderColor: "var(--line-strong)" }}
            >
              Browse the news
            </Link>
          </div>
          <p className="mt-[18px] text-xs" style={{ color: "var(--ink-faint)" }}>
            Every value traces to a source. Free while we build — no account needed.
          </p>
        </div>
        {/* Right: the lens-flip demo IS the hero visual (exact 2a content). */}
        <HeroLensDemo />
      </section>

      {/* ── Open lens registry ───────────────────────────────── */}
      <Reveal
        as="section"
        className="border-y py-11 lg:py-12"
        style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
      >
        <div className="grid items-center gap-10 lg:grid-cols-[360px_1fr] lg:gap-14">
          <div>
            <h2 className="text-[26px] font-semibold leading-tight sm:text-[32px]" style={{ fontFamily: "var(--font-display), serif" }}>
              Your profession is a lens — and lenses are an open set.
            </h2>
            <p className="mt-3.5 text-[14.5px] leading-[1.7]" style={{ color: "var(--ink-muted)" }}>
              A lens is a declaration: which fields get extracted, how your feed ranks, what the
              agent asks. Thirty-plus professions already map onto the backbone — a new one is a
              registry entry, never a new pipeline.
            </p>
          </div>
          <div>
            <div className="flex flex-wrap gap-2">
              {ACTIVE_LENSES.map((l) => (
                <span
                  key={l.name}
                  className="inline-flex items-center gap-[7px] rounded-full px-4 py-[7px] text-[13px] font-semibold"
                  style={{ background: l.bg, color: l.color, boxShadow: `inset 0 0 0 1.5px ${l.color}` }}
                >
                  <span className="h-[7px] w-[7px] rounded-full" style={{ background: l.color }} />
                  {l.name}
                </span>
              ))}
            </div>
            <div className="mt-2.5 flex flex-wrap gap-2">
              {UPCOMING_LENSES.map((l) => (
                <span
                  key={l.name}
                  className="inline-flex items-center gap-[7px] rounded-full border border-dashed px-4 py-[7px] text-[13px] font-semibold"
                  style={{ borderColor: l.muted ? "var(--line-strong)" : l.color, color: l.color }}
                >
                  {l.name}
                  {l.tag && (
                    <span className="font-mono text-[9px] uppercase opacity-70">{l.tag}</span>
                  )}
                </span>
              ))}
            </div>
            <p className="mt-3.5 text-xs" style={{ color: "var(--ink-faint)" }}>
              Trader, CISO, policy analyst, doctor, founder, journalist, student — each maps to a
              lens with its own ranking, fields, and questions.
            </p>
          </div>
        </div>
      </Reveal>

      {/* ── Both Sides ───────────────────────────────────────── */}
      <Reveal as="section" className="grid items-center gap-10 py-16 lg:grid-cols-[420px_1fr] lg:gap-14">
        <div>
          <Eyebrow>Both Sides</Eyebrow>
          <h2 className="text-[28px] font-semibold leading-tight sm:text-[34px]" style={{ fontFamily: "var(--font-display), serif" }}>
            The same ruling is two different stories.
          </h2>
          <p className="mt-4 text-[15px] leading-[1.7]" style={{ color: "var(--ink-muted)" }}>
            Prism groups a story&apos;s sources by stance, side by side, with every outlet&apos;s
            origin and affiliation labeled. You see every framing —{" "}
            <strong style={{ color: "var(--ink)" }}>and who is speaking</strong>.
          </p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2">
          {BOTH_SIDES.map((s) => (
            <Card key={s.label} className="p-5">
              <div className="mb-2 flex flex-wrap items-center gap-2">
                <span className="text-sm font-semibold">{s.label}</span>
                <span className="whitespace-nowrap rounded-full px-[9px] py-0.5 text-[11px] font-semibold" style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
                  {s.region}
                </span>
              </div>
              <p className="text-[13px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
                {s.body}
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {s.sources.map((src) => (
                  <span key={src.name} className="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11.5px]" style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
                    {src.name}
                    {src.funding && (
                      <span className="rounded-full border px-[7px] py-px font-mono text-[9px] uppercase" style={{ borderColor: "var(--line-strong)", color: "var(--ink-faint)" }}>
                        {src.funding}
                      </span>
                    )}
                  </span>
                ))}
              </div>
            </Card>
          ))}
        </div>
      </Reveal>

      {/* ── How it works ─────────────────────────────────────── */}
      <Reveal as="section" className="pb-16">
        <h2 className="mb-[26px] text-center text-[28px] font-semibold tracking-tight sm:text-[32px]" style={{ fontFamily: "var(--font-display), serif" }}>
          How Prism reads the news
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_STEPS.map((s) => (
            <Card key={s.n} className="p-5">
              <div className="text-[26px] font-semibold" style={{ fontFamily: "var(--font-display), serif", color: "var(--ink-faint)" }}>
                {s.n}
              </div>
              <h3 className="mb-1.5 mt-2.5 text-[15px] font-semibold">{s.title}</h3>
              <p className="text-[13px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
                {s.body}
              </p>
            </Card>
          ))}
        </div>
      </Reveal>

      {/* ── So What ──────────────────────────────────────────── */}
      <Reveal as="section" className="grid items-center gap-10 pb-16 lg:grid-cols-[420px_1fr] lg:gap-14">
        <div>
          <Eyebrow>So What</Eyebrow>
          <h2 className="text-[28px] font-semibold leading-tight sm:text-[34px]" style={{ fontFamily: "var(--font-display), serif" }}>
            What happens next — spelled out.
          </h2>
          <p className="mt-4 text-[15px] leading-[1.7]" style={{ color: "var(--ink-muted)" }}>
            Every story carries its consequence graph: who is affected first, and the likely
            second-order effects — each with a direction and a horizon, never vague.
          </p>
        </div>
        <Card className="px-7 pb-6 pt-5">
          <p className="mb-3.5 text-[13.5px] font-semibold leading-[1.45]">
            &ldquo;AI-chip export rules eased for allied markets&rdquo;{" "}
            <span className="font-mono text-[10.5px] font-normal" style={{ color: "var(--ink-faint)" }}>
              — 21 sources
            </span>
          </p>
          <div className="flex flex-col gap-3">
            {CONSEQUENCES.map((c, i) => (
              <div key={i} className={`flex gap-2.5 text-[13.5px] leading-[1.55] ${c.child ? "ml-7" : ""}`}>
                <span style={{ color: c.color }}>{c.glyph}</span>
                <span>
                  <strong>{c.entity}</strong> <span style={{ color: "var(--ink-muted)" }}>— {c.effect}</span>{" "}
                  <span className="font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>· {c.horizon}</span>
                </span>
              </div>
            ))}
          </div>
        </Card>
      </Reveal>

      {/* ── Blindspots + Ask ─────────────────────────────────── */}
      <Reveal as="section" className="grid gap-6 pb-16 lg:grid-cols-2">
        <Card pop className="p-8">
          <Eyebrow>Blindspots</Eyebrow>
          <h2 className="text-[24px] font-semibold leading-tight sm:text-[26px]" style={{ fontFamily: "var(--font-display), serif" }}>
            Some stories you only ever hear one way.
          </h2>
          <p className="mt-3 text-sm leading-[1.7]" style={{ color: "var(--ink-muted)" }}>
            A blindspot is any story where only one side is speaking — every source from one
            country, or every outlet aligned with one party. Prism measures who&apos;s telling each
            story and flags what&apos;s missing.
          </p>
          {BLINDSPOTS.map((b, i) => (
            <div key={i} className={`rounded-2xl border p-[14px] px-[18px] ${i === 0 ? "mt-[18px]" : "mt-2.5"}`} style={{ borderColor: "var(--line)", background: "var(--bg)" }}>
              <div className="mb-2 flex flex-wrap gap-1.5">
                {b.tags.map((t, j) => (
                  <span key={t} className={`whitespace-nowrap rounded-full px-[9px] py-0.5 font-semibold ${j === 1 ? "text-[10.5px] uppercase" : "text-[11px]"}`} style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}>
                    {t}
                  </span>
                ))}
              </div>
              <p className="text-sm font-semibold leading-[1.45]">{b.title}</p>
              <p className="mt-1.5 text-xs" style={{ color: "var(--ink-faint)" }}>
                {b.note}
              </p>
            </div>
          ))}
        </Card>

        <Card pop className="overflow-hidden">
          <div className="px-8 pt-8">
            <Eyebrow>Ask</Eyebrow>
            <h2 className="text-[24px] font-semibold leading-tight sm:text-[26px]" style={{ fontFamily: "var(--font-display), serif" }}>
              Ask anything. Get sources — or honesty.
            </h2>
          </div>
          <div className="flex flex-col gap-3 px-8 pb-6 pt-4">
            <div className="flex items-center gap-2">
              <span className="inline-flex items-center gap-1.5 rounded-full border px-[11px] py-[3px] text-[11px] font-semibold" style={{ borderColor: "var(--line)", color: "var(--ink)" }}>
                <span className="spectrum-text">◮</span>Prism AI agent
              </span>
              <span className="font-mono text-[10px] uppercase tracking-wide" style={{ color: "var(--ink-faint)" }}>
                Grounded in 9 sources
              </span>
            </div>
            <p className="text-xs font-semibold" style={{ color: "var(--ink-faint)" }}>
              On: &ldquo;India names T20 World Cup squad — three debutants, a shock omission&rdquo;
            </p>
            <p className="max-w-[85%] self-end rounded-[16px_16px_4px_16px] px-3.5 py-[9px] text-[13px] leading-[1.55]" style={{ background: "var(--ink)", color: "var(--bg)" }}>
              Why was the vice-captain dropped?
            </p>
            <div className="flex max-w-[92%] gap-2.5">
              <span className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full border" style={{ borderColor: "var(--line)" }}>
                <span className="spectrum-text text-[13px]">◮</span>
              </span>
              <p className="rounded-[4px_16px_16px_16px] px-3.5 py-[9px] text-[13px] leading-[1.6]" style={{ color: "var(--ink)", background: "var(--bg-sunken)" }}>
                Selectors cited workload management after the IPL season{" "}
                <span className="font-mono text-[11px]">[3]</span>; two reports add a fitness-test
                result from the June camp <span className="font-mono text-[11px]">[6][8]</span>.
              </p>
            </div>
            <p className="max-w-[85%] self-end rounded-[16px_16px_4px_16px] px-3.5 py-[9px] text-[13px] leading-[1.55]" style={{ background: "var(--ink)", color: "var(--bg)" }}>
              Will India win the cup?
            </p>
            <div className="flex max-w-[92%] gap-2.5">
              <span className="flex h-[26px] w-[26px] shrink-0 items-center justify-center rounded-full border" style={{ borderColor: "var(--line)" }}>
                <span className="spectrum-text text-[13px]">◮</span>
              </span>
              <div className="rounded-[4px_16px_16px_16px] px-3.5 py-[9px]" style={{ background: "var(--bg-sunken)" }}>
                <span className="mb-[5px] inline-block whitespace-nowrap rounded-full border px-[9px] py-px font-mono text-[10px] uppercase tracking-wide" style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}>
                  Not in sources
                </span>
                <p className="text-[13px] leading-[1.55]">The sources for this story don&apos;t cover that.</p>
              </div>
            </div>
            <div className="flex items-center gap-2.5 rounded-full border px-4 py-[9px]" style={{ borderColor: "var(--line-strong)", background: "var(--bg)" }}>
              <span className="flex-1 text-[13px]" style={{ color: "var(--ink-faint)" }}>Ask anything about this story…</span>
              <span className="flex h-[30px] w-[30px] items-center justify-center rounded-full text-sm" style={{ background: "var(--ink)", color: "var(--bg)" }}>↑</span>
            </div>
            <p className="text-[11.5px]" style={{ color: "var(--ink-faint)" }}>
              Refusal is a feature — the agent never asserts beyond a story&apos;s own sources.
            </p>
          </div>
        </Card>
      </Reveal>

      {/* ── CTA ──────────────────────────────────────────────── */}
      <section className="pb-[72px]">
        <div className="relative overflow-hidden rounded-[22px] border px-6 py-11 text-center" style={{ borderColor: "var(--line)" }}>
          <div className="spectrum-bar absolute inset-x-0 top-0 h-[3px]" aria-hidden />
          <h2 className="text-[28px] font-semibold tracking-tight sm:text-[32px]" style={{ fontFamily: "var(--font-display), serif" }}>
            Pick your lens. Keep the whole spectrum.
          </h2>
          <p className="mx-auto mt-2.5 max-w-[420px] text-sm" style={{ color: "var(--ink-muted)" }}>
            Tell us what you do — your feed, your fields, your questions follow. Your profile lives
            in this browser.
          </p>
          <Link
            href="/onboarding"
            className="mt-[26px] inline-block rounded-full px-8 py-[13px] text-sm font-semibold transition hover:opacity-85"
            style={{ background: "var(--ink)", color: "var(--bg)" }}
          >
            Choose your lens →
          </Link>
        </div>
      </section>
    </div>
  );
}
