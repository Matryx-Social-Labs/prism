import Link from "next/link";

const LABELS = [
  {
    chip: "State-affiliated",
    chipStyle: { border: "1px solid var(--line-strong)", color: "var(--ink-muted)" },
    body: "The outlet is funded or editorially directed by a government. Its reporting still counts — you just always know who's speaking.",
  },
  {
    chip: "Public broadcaster",
    chipStyle: { border: "1px solid var(--line-strong)", color: "var(--ink-muted)" },
    body: "Publicly funded with editorial independence mandates (BBC, DW). Distinct from state-affiliated — the difference matters, so we label both.",
  },
  {
    chip: "⚠ Single-origin",
    chipStyle: { background: "var(--bg-sunken)", color: "var(--ink-muted)" },
    body: "Every source on the story shares one origin country. You're seeing one side because only one side is speaking — the blindspot flag.",
  },
  {
    chip: "◉ Your region",
    chipStyle: { background: "var(--bg-sunken)", color: "var(--ink-muted)" },
    body: "The story involves or is covered from your region. Your feed blends these with international coverage — never one without the other.",
  },
];

export default function AboutPage() {
  return (
    <div className="mx-auto max-w-[760px] px-5 pb-20 pt-11 sm:px-8">
      <p className="mb-3.5 text-[11.5px] font-semibold uppercase tracking-[0.3em]" style={{ color: "var(--ink-faint)" }}>
        Why Prism exists
      </p>
      <h1
        className="text-[36px] font-semibold leading-[1.15] tracking-tight"
        style={{ fontFamily: "var(--font-display), serif" }}
      >
        News is one-sided because you only ever see one side.
      </h1>
      <p className="mt-[18px] text-[15.5px] leading-[1.75]" style={{ color: "var(--ink-muted)" }}>
        A side is a narrative: a political story has two narrations, and most readers only ever
        hear one of them. Prism merges the many reports of one real event into a single canonical
        story and shows the competing narratives side by side — backed by deliberately diverse
        sourcing across many origin countries and transparency labels on every outlet, so you
        always know who is speaking. Then <strong style={{ color: "var(--ink)" }}>you</strong> decide.
      </p>

      <h2 className="mb-3.5 mt-10 text-[22px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        What the labels mean
      </h2>
      <div className="flex flex-col gap-3.5">
        {LABELS.map((l) => (
          <div
            key={l.chip}
            className="flex items-baseline gap-3.5 rounded-2xl border px-[18px] py-4"
            style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}
          >
            <span
              className="inline-block shrink-0 rounded-full px-[11px] py-[3px] text-[10.5px] font-semibold uppercase tracking-wide"
              style={l.chipStyle}
            >
              {l.chip}
            </span>
            <p className="text-[13.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
              {l.body}
            </p>
          </div>
        ))}
      </div>

      <h2 className="mb-3.5 mt-10 text-[22px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        Nothing without provenance
      </h2>
      <p className="text-[14.5px] leading-[1.75]" style={{ color: "var(--ink-muted)" }}>
        Every extracted value — a CVSS score, a ticker, a casualty count — keeps a link to the
        exact source that evidenced it. The Ask agent answers only from a story&apos;s own sources,
        cites them by number, and refuses what they don&apos;t cover. Refusal is styled with the
        same dignity as an answer, because knowing the limits of the evidence <em>is</em> the
        product.
      </p>

      <div className="mt-9 flex flex-wrap gap-3">
        <Link
          href="/feed"
          className="rounded-full px-[26px] py-3 text-sm font-semibold transition hover:opacity-85"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          Browse the news
        </Link>
        <Link
          href="/onboarding"
          className="rounded-full border px-[26px] py-3 text-sm font-semibold transition hover:opacity-70"
          style={{ borderColor: "var(--line-strong)" }}
        >
          Choose your lens
        </Link>
      </div>
    </div>
  );
}
