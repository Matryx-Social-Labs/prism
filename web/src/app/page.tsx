import Link from "next/link";

const PILLARS = [
  {
    title: "Both Sides",
    body: "Every story's sources grouped by stance and origin — vendor advisories next to researcher warnings, official framing next to independent reporting. See who says what before deciding what to believe.",
    accent: "border-sky-500",
  },
  {
    title: "So What",
    body: "An impact graph, not just a headline: who is affected, what happens next, and — for your role — what it means for your controls, your stack, or your positions.",
    accent: "border-amber-500",
  },
  {
    title: "Ask",
    body: "A per-story agent that answers follow-up questions from that story's own sources, with citations. If the sources don't cover it, it says so instead of guessing.",
    accent: "border-emerald-500",
  },
];

const LENSES = [
  {
    name: "Cybersecurity / GRC",
    desc: "CVEs with CVSS, exploitation status, affected products, and NIST/CIS control mapping. From a new CVE to “does this affect me and what do I do” in under a minute.",
    live: true,
  },
  {
    name: "Finance / Trader",
    desc: "Market-moving news with tickers, catalysts, and evidence-based price-impact reads.",
    live: true,
  },
  {
    name: "Your role",
    desc: "Lenses are declarative add-ons over one shared pipeline — new roles ship without a rewrite.",
    live: false,
  },
];

export default function LandingPage() {
  return (
    <div className="space-y-20 pb-16">
      {/* Hero */}
      <section className="pt-12 text-center">
        <p className="mb-3 text-xs font-semibold uppercase tracking-[0.25em] text-stone-500">
          Role-aware news intelligence
        </p>
        <h1 className="mx-auto max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">
          Every story, split into its full spectrum.
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-stone-600 dark:text-stone-400">
          Prism clusters worldwide coverage into single events, shows you every side,
          maps the consequences for <em>your</em> role, and answers your questions —
          grounded in the story&apos;s own sources, never beyond them.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            href="/onboarding"
            className="rounded-lg bg-stone-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-stone-700 dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-300"
          >
            Get your feed
          </Link>
          <Link
            href="/feed"
            className="rounded-lg border border-stone-300 px-6 py-3 text-sm font-semibold transition hover:bg-stone-100 dark:border-stone-700 dark:hover:bg-stone-900"
          >
            Browse without a profile
          </Link>
        </div>
      </section>

      {/* Three-part promise */}
      <section>
        <h2 className="mb-2 text-center text-2xl font-bold">The promise, per story</h2>
        <p className="mb-8 text-center text-sm text-stone-500">
          Not more headlines faster — the full picture of each one.
        </p>
        <div className="grid gap-4 sm:grid-cols-3">
          {PILLARS.map((p) => (
            <div key={p.title} className={`rounded-xl border-t-4 ${p.accent} border border-stone-200 p-5 dark:border-stone-800`}>
              <h3 className="mb-2 text-lg font-bold">{p.title}</h3>
              <p className="text-sm leading-relaxed text-stone-600 dark:text-stone-400">{p.body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section className="rounded-2xl border border-stone-200 p-8 dark:border-stone-800">
        <h2 className="mb-6 text-center text-2xl font-bold">One pipeline, many lenses</h2>
        <div className="mx-auto max-w-2xl space-y-3 text-sm leading-relaxed text-stone-600 dark:text-stone-400">
          <p>
            Prism continuously ingests authoritative feeds (NVD, CISA KEV) and worldwide news,
            gates out noise, extracts typed facts with field-level source provenance, and merges
            the many reports of one real event into a single canonical story.
          </p>
          <p>
            Your role selects a <strong className="text-stone-900 dark:text-stone-100">lens</strong>:
            the extra fields extracted, how your feed is ranked, and the questions the agent
            suggests. Every value on every story traces back to the source that evidenced it.
          </p>
        </div>
      </section>

      {/* Lenses */}
      <section>
        <h2 className="mb-8 text-center text-2xl font-bold">Built for your role</h2>
        <div className="grid gap-4 sm:grid-cols-3">
          {LENSES.map((lens) => (
            <div key={lens.name} className="rounded-xl border border-stone-200 p-5 dark:border-stone-800">
              <div className="mb-2 flex items-center gap-2">
                <h3 className="font-bold">{lens.name}</h3>
                {lens.live ? (
                  <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-semibold text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300">
                    live
                  </span>
                ) : (
                  <span className="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-semibold text-stone-500 dark:bg-stone-900">
                    coming
                  </span>
                )}
              </div>
              <p className="text-sm leading-relaxed text-stone-600 dark:text-stone-400">{lens.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Bottom CTA */}
      <section className="text-center">
        <h2 className="text-2xl font-bold">Trust what you read — because you can check it.</h2>
        <p className="mx-auto mt-3 max-w-xl text-sm text-stone-500">
          Prototype: cybersecurity &amp; GRC and finance lenses, free while we build.
        </p>
        <Link
          href="/onboarding"
          className="mt-6 inline-block rounded-lg bg-stone-900 px-6 py-3 text-sm font-semibold text-white transition hover:bg-stone-700 dark:bg-stone-100 dark:text-stone-900 dark:hover:bg-stone-300"
        >
          Choose your lens →
        </Link>
      </section>
    </div>
  );
}
