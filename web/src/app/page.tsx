import Link from "next/link";
import { HeroVisual } from "@/components/HeroVisual";
import { LensDemo } from "@/components/LensDemo";
import { Reveal } from "@/components/Reveal";

const ORIGINS = [
  "India",
  "United Kingdom",
  "Qatar",
  "Germany",
  "France",
  "Turkey",
  "Hong Kong",
  "Pakistan",
  "Russia",
  "China",
  "Iran",
];

const HOW_STEPS = [
  {
    n: "01",
    title: "Cluster",
    body: "Fifty duplicate headlines about one real event become a single canonical story with every source attached.",
  },
  {
    n: "02",
    title: "Balance",
    body: "Each story's coverage-origin mix is measured. One origin only? It's flagged as a blindspot.",
  },
  {
    n: "03",
    title: "Lens",
    body: "Written briefs re-read the same event for each profession — reader, cyber, markets. More lenses join the same backbone.",
  },
  {
    n: "04",
    title: "Ground",
    body: "Ask anything. The agent answers from the story's own sources with citations — or refuses, visibly.",
  },
];

const PERSONAS = [
  {
    color: "var(--lens-general)",
    name: "For everyone staying informed",
    points: [
      "World news clustered into single stories — not fifty duplicate headlines",
      "Both sides of every contested story, grouped by stance and origin",
      "What happens next: the consequence graph behind each event",
      "Ask anything — answers cite the story's own sources or say so",
    ],
  },
  {
    color: "var(--lens-cyber)",
    name: "For cybersecurity & GRC",
    points: [
      "CVEs with CVSS, exploitation status, and affected products — minutes after disclosure",
      "Every story mapped to your controls: NIST 800-53, CIS",
      "World events read as threat intelligence: who's exposed, what to check",
      "From a new CVE to “does this affect me” in under a minute",
    ],
  },
  {
    color: "var(--lens-finance)",
    name: "For markets & trading",
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
    body: "Answers cite the story's own sources; when the sources don't cover it, the agent says so instead of inventing.",
  },
  {
    title: "Both sides, by design",
    body: "Sources are grouped by stance and country of origin, so you see how each side frames the same event — before deciding what to believe.",
  },
];

export default function LandingPage() {
  return (
    <div className="mx-auto max-w-[1080px] px-5">
      {/* ── Hero ─────────────────────────────────────────────── */}
      <section className="grid items-center gap-12 pb-14 pt-12 sm:pt-[72px] lg:grid-cols-[1.05fr_0.95fr]">
        <div>
          <p
            className="mb-4 text-[11.5px] font-semibold uppercase tracking-[0.3em]"
            style={{ color: "var(--ink-faint)" }}
          >
            Role-aware news intelligence
          </p>
          <h1
            className="text-[42px] font-semibold leading-[1.02] tracking-tight sm:text-[64px]"
            style={{ fontFamily: "var(--font-display), serif" }}
          >
            One event.
            <br />
            <span className="spectrum-text">Every angle.</span>
          </h1>
          <p className="mt-[22px] max-w-[480px] text-[17px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
            Prism clusters worldwide coverage into single events, then reads each one through{" "}
            <em>your</em> professional lens. A war is a humanitarian story, a cyber-risk window,
            and a market catalyst at once — switch the lens and the same news changes meaning.
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
        <HeroVisual />
      </section>

      {/* ── Live lens demo ───────────────────────────────────── */}
      <Reveal as="section" className="pb-16 pt-10">
        <div className="mx-auto mb-7 max-w-[560px] text-center">
          <h2 className="text-[32px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            Same story. Different stakes.
          </h2>
          <p className="mt-2 text-sm" style={{ color: "var(--ink-muted)" }}>
            Flip the lens on a real event and watch the read change.
          </p>
        </div>
        <div className="mx-auto max-w-[680px]">
          <LensDemo />
        </div>
        <p className="mt-4 text-center text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
          Briefs are written per lens from the story&apos;s own sources — nothing is asserted
          without provenance.
        </p>
      </Reveal>

      {/* ── Origin diversity ─────────────────────────────────── */}
      <Reveal as="section" className="border-t pb-16 pt-6" style={{ borderColor: "var(--line)" }}>
        <div className="grid items-center gap-10 lg:grid-cols-2">
          <div>
            <h2 className="text-[32px] font-semibold leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
              Most people only ever see one country&apos;s version.
            </h2>
            <p className="mt-3.5 text-[15px] leading-[1.7]" style={{ color: "var(--ink-muted)" }}>
              Prism deliberately ingests outlets across many origin countries, labels
              state-affiliated and public broadcasters transparently, and measures every story&apos;s
              coverage-origin balance. You see every side —{" "}
              <strong style={{ color: "var(--ink)" }}>and who is speaking</strong>.
            </p>
          </div>
          <div>
            <div className="flex flex-wrap gap-2">
              {ORIGINS.map((c) => (
                <span
                  key={c}
                  className="rounded-full border px-[13px] py-[5px] text-[12.5px] font-medium"
                  style={{ borderColor: "var(--line)", color: "var(--ink-muted)", background: "var(--bg-elevated)" }}
                >
                  {c}
                </span>
              ))}
            </div>
            <div className="mt-3.5 flex flex-wrap gap-2">
              <span
                className="rounded-full border px-[11px] py-1 text-[10.5px] font-semibold uppercase tracking-wide"
                style={{ borderColor: "var(--line)", color: "var(--ink-faint)" }}
              >
                State-affiliated
              </span>
              <span
                className="rounded-full border px-[11px] py-1 text-[10.5px] font-semibold uppercase tracking-wide"
                style={{ borderColor: "var(--line)", color: "var(--ink-faint)" }}
              >
                Public broadcaster
              </span>
              <span
                className="rounded-full px-[11px] py-1 text-[10.5px] font-semibold uppercase tracking-wide"
                style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}
              >
                ⚠ Single-origin flag
              </span>
            </div>
            <p className="mt-3 text-[12.5px]" style={{ color: "var(--ink-faint)" }}>
              Labels ride with every outlet, everywhere it appears.
            </p>
          </div>
        </div>
      </Reveal>

      {/* ── How it works ─────────────────────────────────────── */}
      <Reveal as="section" className="pb-16">
        <h2
          className="mb-[26px] text-center text-[32px] font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display), serif" }}
        >
          How Prism reads the news
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {HOW_STEPS.map((s) => (
            <div
              key={s.n}
              className="rounded-[18px] border p-5"
              style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
            >
              <div
                className="text-[26px] font-semibold"
                style={{ fontFamily: "var(--font-display), serif", color: "var(--ink-faint)" }}
              >
                {s.n}
              </div>
              <h3 className="mb-1.5 mt-2.5 text-[15px] font-semibold">{s.title}</h3>
              <p className="text-[13px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
                {s.body}
              </p>
            </div>
          ))}
        </div>
      </Reveal>

      {/* ── Blindspots ───────────────────────────────────────── */}
      <Reveal as="section" className="pb-16">
        <div
          className="rounded-[22px] border p-8"
          style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", boxShadow: "var(--shadow-card)" }}
        >
          <div className="grid items-center gap-9 lg:grid-cols-2">
            <div>
              <p className="mb-2.5 text-[11px] font-semibold uppercase tracking-[0.2em]" style={{ color: "var(--ink-faint)" }}>
                Blindspots
              </p>
              <h2 className="text-[28px] font-semibold leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
                Some stories only one country tells.
              </h2>
              <p className="mt-3 text-[14.5px] leading-[1.7]" style={{ color: "var(--ink-muted)" }}>
                When every source on a story shares one origin, Prism flags it — so you know
                you&apos;re seeing one side because only one side is speaking.
              </p>
            </div>
            <div
              className="rounded-2xl border p-[18px] text-left"
              style={{ borderColor: "var(--line)", background: "var(--bg)" }}
            >
              <div className="mb-2.5 flex flex-wrap gap-1.5">
                <span
                  className="rounded-full px-[9px] py-0.5 text-[11px] font-semibold"
                  style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}
                >
                  ⚠ Single-origin coverage
                </span>
                <span
                  className="rounded-full px-[9px] py-0.5 text-[11px] font-semibold"
                  style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}
                >
                  One origin × all sources
                </span>
              </div>
              <p className="text-[15px] font-semibold leading-[1.45]" style={{ color: "var(--ink)" }}>
                Prism flags stories the rest of the world&apos;s media hasn&apos;t picked up yet.
              </p>
              <p className="mt-2 text-xs" style={{ color: "var(--ink-faint)" }}>
                “No outlet from your region has covered this yet” → read it anyway, aware.
              </p>
            </div>
          </div>
        </div>
      </Reveal>

      {/* ── Personas ─────────────────────────────────────────── */}
      <Reveal as="section" className="pb-16">
        <h2
          className="mb-[26px] text-center text-[32px] font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display), serif" }}
        >
          Built for how you read the world
        </h2>
        <div className="grid gap-[18px] lg:grid-cols-3">
          {PERSONAS.map((p) => (
            <div
              key={p.name}
              className="card-hover rounded-[18px] border p-6"
              style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
            >
              <div className="mb-4 h-1 w-10 rounded-full" style={{ background: p.color }} />
              <h3 className="text-[16.5px] font-semibold">{p.name}</h3>
              <ul className="mt-3.5 flex flex-col gap-[11px]">
                {p.points.map((pt) => (
                  <li key={pt} className="flex gap-2.5 text-[13.5px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>
                    <span aria-hidden style={{ color: p.color }}>
                      ◆
                    </span>
                    <span>{pt}</span>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
        <p className="mt-5 text-center text-[13.5px]" style={{ color: "var(--ink-muted)" }}>
          New roles are lenses on the same backbone — not new products. More lenses are on the way.
        </p>
      </Reveal>

      {/* ── Trust ────────────────────────────────────────────── */}
      <Reveal as="section" className="pb-16">
        <h2
          className="mb-[26px] text-center text-[32px] font-semibold tracking-tight"
          style={{ fontFamily: "var(--font-display), serif" }}
        >
          Trust what you read — because you can check it
        </h2>
        <div className="grid gap-[18px] lg:grid-cols-3">
          {TRUST.map((t) => (
            <div key={t.title} className="rounded-[18px] border p-6" style={{ borderColor: "var(--line)" }}>
              <h3 className="text-[15.5px] font-semibold">{t.title}</h3>
              <p className="mt-2.5 text-[13.5px] leading-[1.65]" style={{ color: "var(--ink-muted)" }}>
                {t.body}
              </p>
            </div>
          ))}
        </div>
        <div
          className="mx-auto mt-7 max-w-[560px] rounded-2xl border px-5 py-[18px]"
          style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
        >
          <p className="mb-2 text-xs font-semibold" style={{ color: "var(--ink-faint)" }}>
            You asked: “Will oil hit $100?”
          </p>
          <div className="flex items-baseline gap-2.5">
            <span
              className="shrink-0 rounded-full border px-2.5 py-0.5 text-[10.5px] font-semibold uppercase tracking-wide"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink-muted)" }}
            >
              Not in sources
            </span>
            <p className="text-sm leading-[1.6]" style={{ color: "var(--ink)" }}>
              The sources for this story don&apos;t cover that.
            </p>
          </div>
          <p className="mt-2.5 text-xs" style={{ color: "var(--ink-faint)" }}>
            Refusal is a feature. The agent answers only from a story&apos;s own sources — and says
            so when it can&apos;t.
          </p>
        </div>
      </Reveal>

      {/* ── CTA ──────────────────────────────────────────────── */}
      <section className="pb-[72px]">
        <div
          className="relative overflow-hidden rounded-[22px] border px-6 py-11 text-center"
          style={{ borderColor: "var(--line)" }}
        >
          <div className="spectrum-bar absolute inset-x-0 top-0 h-[3px]" aria-hidden />
          <h2 className="text-[32px] font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
            Pick your lens. Keep the whole spectrum.
          </h2>
          <p className="mx-auto mt-2.5 max-w-[420px] text-sm" style={{ color: "var(--ink-muted)" }}>
            Three quick questions and your feed is ready. Your profile lives in this browser.
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
