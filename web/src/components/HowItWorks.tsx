import { CONTACT_EMAIL, LEGAL_ENTITY } from "@/lib/legal";
import { sentences } from "@/lib/sentences";
import Link from "next/link";
import { AskDemo } from "@/components/AskDemo";
import { ChartRow } from "@/components/ChartRow";
import { CoverageBar, CoverageLegend, MonogramStack, OutletIcon } from "@/components/Coverage";
import { EntityText } from "@/components/EntityText";
import { HeroLensDemo } from "@/components/HeroLensDemo";
import { LensRegistry } from "@/components/LensRegistry";
import { PrismFigure } from "@/components/PrismFigure";
import { ReportCard } from "@/components/SourceList";
import { Reveal } from "@/components/Reveal";
import { Said } from "@/components/Said";
import { StepRail } from "@/components/StepRail";
import { AVAILABLE, NEXT, StatusColumn, VALIDATION } from "@/components/StatusGrid";
import { ArrowRight } from "@/components/icons";
import { fetchEvent, fetchFeed, type EventDetail, type FeedItem, type OutletRef } from "@/lib/api";
import { coverageText, languageNames, languagesOf, publishers, type Origin } from "@/lib/coverage";
import { relativeTime } from "@/lib/dateline";
import { indexSources } from "@/lib/sources";

/**
 * How Prism works (/about): one real story from today's record, followed
 * through the product step by step — the reports as they came in, the one
 * record they became, who covered it, who said what, the brief written from
 * them, the same facts read through a lens, and a question answered from the
 * reports. Every example is live and counted; the two illustrations are
 * labelled. Then what Prism refuses to do, where it stands, and the door in.
 * Steps print in as they are reached (Reveal); reduced motion shows them.
 */
const SHELL = "mx-auto w-full max-w-[var(--shell)] px-5 sm:px-8 xl:px-10";

const STEPS = [
  { id: "reports", n: "01", label: "Reports come in" },
  { id: "record", n: "02", label: "One record" },
  { id: "coverage", n: "03", label: "Who covered it" },
  { id: "said", n: "04", label: "Who said what" },
  { id: "brief", n: "05", label: "The brief" },
  { id: "lens", n: "06", label: "Read it through a lens" },
  { id: "ask", n: "07", label: "Ask the record" },
  { id: "refuses", n: "08", label: "What Prism refuses" },
];

const REFUSALS: [string, string][] = [
  ["No invented numbers.", "Every count on a page is counted from the reports: outlets, languages, quotes, developments. If it is not countable, it is not printed."],
  ["No unsourced lines.", "A quote appears only when the same words are in the article. The brief is written from the reports below it and says so."],
  ["No left, right or centre.", "Coverage is described by where an outlet comes from, a fact of the source, not by a rating nobody has made for Indian outlets."],
  ["No photos of its own.", "A picture is only ever the outlet's, shown as a credited link preview of that outlet's report, never as Prism's."],
  ["No silent edits.", "Every record shows when it was last updated; a new report never erases what came before it."],
];

// Editorial accountability, in the vocabulary a reader and a policy review
// both read: who writes a record, what a machine does and does not decide, and
// where a mistake goes. Bylines read "Headline by Prism" — this is the page
// that says what that means.
const ACCOUNTABILITY: [string, string][] = [
  ["A record is written by machine, and says so.", "Every headline, brief and summary on Prism is written by software from the reports listed under it, never by a journalist and never presented as one. That is why a record is bylined \u201CHeadline by Prism\u201D and names the reports it was written from."],
  ["The reporting is the outlets\u2019.", "Prism does not report. It reads what registered outlets published, keeps each report as it was, and links to it. The journalism belongs to the outlet that did it. What Prism adds is the grouping, the counts and the reading."],
  ["A quote is the article\u2019s words or it is not there.", "Quotes are checked against the article they came from before they appear. When a check fails the quote is dropped rather than paraphrased."],
  ["A correction does not overwrite the past.", "A record carries the time it was last updated, and a later report is added to it rather than replacing what came before. Where a record is wrong it is fixed, and it stays dated."],
];

type Example = { row: FeedItem; event: EventDetail; outlets: OutletRef[] };

/** Registered-source facts from a record's own report list. */
function outletsOf(event: EventDetail): OutletRef[] {
  return event.sources
    .filter((s) => s.code && s.origin)
    .map((s) => ({ slug: s.source_slug, publisher: s.publisher ?? s.source_slug, name: s.source_name, code: s.code!, origin: s.origin as Origin, language: s.language ?? null, domain: s.domain ?? null }));
}

/** The story that shows the most: many outlets, a verified quote, a brief. Falls back gracefully. */
async function pickExample(): Promise<Example | null> {
  try {
    const rows = (await fetchFeed({ limit: 60, scope: "all" })).filter((r) => r.sector !== "cybersecurity");
    const ranked = [...rows].sort((a, b) => (b.source_count ?? 0) - (a.source_count ?? 0)).slice(0, 8);
    const events = (await Promise.all(ranked.map((r) => fetchEvent(r.id).catch(() => null)))).filter((e): e is EventDetail => e !== null);
    const score = (e: EventDetail) => (e.sources.length >= 3 ? 4 : 0) + ((e.claims ?? []).some((c) => c.role) ? 3 : (e.claims ?? []).length > 0 ? 2 : 0) + (e.lens_briefs?.reader ? 1 : 0);
    const best = [...events].sort((a, b) => score(b) - score(a))[0];
    if (!best) return null;
    const row = ranked.find((r) => r.id === best.id)!;
    return { row, event: best, outlets: outletsOf(best) };
  } catch {
    return null;
  }
}


function Step({ id, n, title, rule, children, example }: { id: string; n: string; title: string; rule: string; children: React.ReactNode; example: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24 grid gap-6 border-t py-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-12 lg:py-14" style={{ borderColor: "var(--line)" }} aria-labelledby={`${id}-title`}>
      <div>
        <p className="font-mono text-[11px] tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>STEP {n}</p>
        <h2 id={`${id}-title`} className="font-record mt-2 text-[28px] font-bold leading-[1.15] tracking-[-0.015em] lg:text-[34px]">{title}</h2>
        <div className="mt-3 flex max-w-[46ch] flex-col gap-3 text-[16px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>{children}</div>
        <p className="mt-4 inline-flex items-center gap-2 rounded-[var(--r-sm)] border px-2.5 py-1.5 font-mono text-[11px] tracking-[0.04em]" style={{ borderColor: "var(--line-strong)", color: "var(--ink-2)" }}>
          <span style={{ color: "var(--accent)" }}>RULE</span> {rule}
        </p>
      </div>
      <Reveal className="min-w-0">{example}</Reveal>
    </section>
  );
}

function Unavailable({ what }: { what: string }) {
  return <p className="card text-[14px]" style={{ color: "var(--ink-3)" }}>{what} is not available in the current window.</p>;
}

export async function HowItWorks() {
  const ex = await pickExample();
  const event = ex?.event ?? null;
  const outlets = ex?.outlets ?? [];
  const reports = event ? [...event.sources].sort((a, b) => (a.published_at ?? "").localeCompare(b.published_at ?? "")) : [];
  const quote = event?.claims?.find((c) => c.role) ?? event?.claims?.[0] ?? null;
  const brief = event?.lens_briefs?.reader ?? null;
  const points = brief ? sentences(brief) : [];
  const watch = event?.lens_points?.reader ?? [];
  const langs = languagesOf(outlets);

  return (
    <div className="pb-24 lg:pb-20">
      {/* ── The walk-through's opening: what it is, on which story ── */}
      <section className={`${SHELL} grid gap-8 py-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] lg:items-center lg:gap-14 lg:py-16`}>
        <div>
          <h1 className="font-record max-w-[16ch] text-[38px] font-bold leading-[1.06] tracking-[-0.02em] text-balance sm:text-[48px] lg:text-[56px]">How Prism works</h1>
          <p className="mt-5 max-w-[46ch] text-[17px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
            Prism reads the day&rsquo;s reports from the outlets it monitors and keeps one record per story: what each outlet reported, who said what in their exact words, and a brief written only from those reports. Below, one story from today&rsquo;s record goes through it, step by step.
          </p>
          <div className="mt-6 flex flex-wrap items-center gap-2.5">
            <a href="#reports" className="btn btn-primary btn-lg">Start with the reports <ArrowRight /></a>
            <Link href="/feed" className="btn btn-ghost btn-lg">Open today&rsquo;s record</Link>
          </div>
        </div>
        <div>
          <PrismFigure className="mx-auto mb-5 block w-full max-w-[480px]" />
          {ex ? (
            <div className="card">
              <p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Today&rsquo;s example · live</p>
              <Link href={`/story/${event!.id}`} className="font-record mt-2 block text-[22px] font-bold leading-[1.25] text-balance underline-offset-4 hover:underline">{event!.title}</Link>
              <p className="mt-2 font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>
                {coverageText(outlets, event!.sources.length)} · {event!.sources.length} {event!.sources.length === 1 ? "report" : "reports"}{langs.length ? ` · ${languageNames(langs)}` : ""} · updated {relativeTime(event!.last_updated_at)}
              </p>
            </div>
          ) : (
            <div className="card" role="status">
              <p className="font-record text-[20px] font-bold leading-[1.25]">The live record is unavailable right now.</p>
              <p className="mt-2 text-[14.5px]" style={{ color: "var(--ink-2)" }}>The steps below still explain how it works; the examples return when the monitored feed reconnects.</p>
            </div>
          )}
        </div>
      </section>

      <div className={`${SHELL} lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-x-10`}>
        <StepRail steps={STEPS} />
        <div className="min-w-0">
          <Step id="reports" n="01" title="Reports come in, and stay as they were." rule="A report is kept as published, with its outlet and time."
            example={<ReportsExample reports={reports} outlets={outlets} />}>
            <p>Prism watches a fixed list of outlets: English national papers, Indian-language papers, the international press and the wires. Every report keeps its own headline, its outlet and the minute it published.</p>
            {event && <p>This story arrived as {event.sources.length} {event.sources.length === 1 ? "report" : "reports"} from {publishers(outlets).length || event.sources.length} {publishers(outlets).length === 1 ? "outlet" : "outlets"}{langs.length > 1 ? ` in ${langs.length} languages` : ""}.</p>}
          </Step>

          <Step id="record" n="02" title="Many reports become one record." rule="One row per story; the counts are counted, never typed."
            example={ex ? (
              <ol className="chart-print flex flex-col" aria-label="The story as one row on today's record"><ChartRow item={{ ...ex.row, outlets: ex.row.outlets?.length ? ex.row.outlets : outlets }} lead /></ol>
            ) : <Unavailable what="A live row" />}>
            <p>Reports of the same happening are matched into one record. The row you see on Today carries a headline written from the reports (or the first report&rsquo;s own), the outlets behind it, and a coverage bar. Open it and every report is one tap away.</p>
          </Step>

          <Step id="coverage" n="03" title="See who covered it, not who to trust." rule="By outlet origin, a fact of the source. Never left, right or centre."
            example={outlets.length > 0 ? (
              <div className="card">
                <p className="flex flex-wrap items-center gap-3">
                  <MonogramStack outlets={outlets} limit={6} />
                  <CoverageBar outlets={outlets} size="lg" width={220} draw />
                  <span className="font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>{coverageText(outlets)}</span>
                </p>
                <div className="mt-4"><CoverageLegend outlets={outlets} /></div>
                <p className="mt-3 text-[13px]" style={{ color: "var(--ink-3)" }}>{publishers(outlets).map((o) => o.name).join(" · ")}</p>
              </div>
            ) : <Unavailable what="Coverage" />}>
            <p>The bar splits the reporting by where each outlet comes from: English national, Indian-language, international, wire. It answers &ldquo;who has this story?&rdquo; at a glance, and a single-source story is drawn dashed so you know it is thin.</p>
            <p>No Indian outlet has an agreed left/right rating, so Prism does not invent one.</p>
          </Step>

          <Step id="said" n="04" title="Who said what, in their exact words." rule="Verbatim or absent. Every quote links to the line in the article."
            example={event && quote ? (
              <div className="[&_.card]:border-0 [&_.card]:p-0 card">
                <Said claims={[{ ...quote, claims: quote.claims.slice(0, 2) }]} sourceIndex={indexSources(event.sources)} />
              </div>
            ) : <Unavailable what="A verified quote" />}>
            <p>Prism pulls out what named people and bodies said, and keeps a quote only if the same words are in the article. Each one names the speaker and their office as the article gave it, the outlet that carried it, and opens the article at that line.</p>
            {quote?.role && <p>Here: {quote.speaker}, {quote.role}.</p>}
          </Step>

          <Step id="brief" n="05" title="A brief written from the reports below it." rule="Nothing in the brief is unsourced; names link to every story about them."
            example={event && points.length > 0 ? (
              <div className="card">
                <p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>The record · written from {event.sources.length} {event.sources.length === 1 ? "report" : "reports"}</p>
                <ul className="mt-3 flex flex-col gap-2.5 text-[16px] leading-[1.6]">
                  {points.slice(0, 5).map((p, i) => (
                    <li key={i} className="grid grid-cols-[14px_1fr] gap-x-2">
                      <span aria-hidden className="mt-[11px] h-1.5 w-1.5 rounded-full" style={{ background: "var(--ink-3)" }} />
                      <EntityText text={p} entities={event.entities} claims={event.claims ?? []} />
                    </li>
                  ))}
                </ul>
                {watch.length > 0 && (
                  <p className="mt-4 text-[13.5px]" style={{ color: "var(--ink-3)" }}>What to watch: {watch[0]}</p>
                )}
              </div>
            ) : <Unavailable what="A brief" />}>
            <p>Each point is one fact from the reports, written to stand on its own; the last says why it matters. Underlined names are the people and bodies in the story: hover or tap one for who they are and what they said here.</p>
          </Step>

          <Step id="lens" n="06" title="Read the same facts for your work." rule="The record never changes. Only the reading does."
            example={<div className="flex flex-col gap-3"><HeroLensDemo /><p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Illustration · the flip on a sample story</p></div>}>
            <p>A lens is a professional reading of the record: what a story means for markets, or for security teams. Flip it and a scan line re-inks the block; the facts beneath stay exactly where they were.</p>
            <div className="mt-1"><LensRegistry /></div>
          </Step>

          <Step id="ask" n="07" title="Ask, and the answer cites the reports." rule="An answer names its sources or says it cannot tell."
            example={<div className="flex flex-col gap-3"><AskDemo /><p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Illustration</p></div>}>
            <p>Every record has a question box. The answer is written only from that story&rsquo;s own reports and cites them by number; when the reports do not say, it says so instead of guessing.</p>
          </Step>

          <section id="refuses" className="scroll-mt-24 border-t py-10 lg:py-14" style={{ borderColor: "var(--line)" }} aria-labelledby="refuses-title">
            <p className="font-mono text-[11px] tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>STEP 08</p>
            <h2 id="refuses-title" className="font-record mt-2 text-[28px] font-bold leading-[1.15] tracking-[-0.015em] lg:text-[34px]">What Prism refuses to do.</h2>
            <ul className="mt-6 grid gap-x-10 gap-y-5 md:grid-cols-2">
              {REFUSALS.map(([head, body], i) => (
                <li key={head} className="border-t pt-4" style={{ borderColor: "var(--line)" }}>
                  <Reveal delay={i * 40}>
                    <p className="font-record text-[20px] font-bold leading-[1.25]">{head}</p>
                    <p className="mt-1.5 text-[15px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>{body}</p>
                  </Reveal>
                </li>
              ))}
            </ul>
          </section>

          {/* The address `correctionsPolicy` and `publishingPrinciples` point at
              (lib/seo.ts). It carried no `id`, so the schema's /about#status
              resolved to the page and to no anchor on it — and a machine-written
              byline is exactly what a news policy review reads a page like this
              to understand. */}
          <section id="accountability" className="scroll-mt-24 border-t py-10 lg:py-14" style={{ borderColor: "var(--line)" }} aria-labelledby="accountability-title">
            <p className="font-mono text-[11px] tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>STEP 09</p>
            <h2 id="accountability-title" className="font-record mt-2 text-[28px] font-bold leading-[1.15] tracking-[-0.015em] lg:text-[34px]">Who writes this, and how to correct it.</h2>
            <div className="mt-6 grid gap-x-10 gap-y-5 md:grid-cols-2">
              {ACCOUNTABILITY.map(([head, body], i) => (
                <div key={head} className="border-t pt-4" style={{ borderColor: "var(--line)" }}>
                  <Reveal delay={i * 40}>
                    <p className="font-record text-[20px] font-bold leading-[1.25]">{head}</p>
                    <p className="mt-1.5 text-[15px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>{body}</p>
                  </Reveal>
                </div>
              ))}
            </div>
            <p className="mt-5 max-w-[64ch] text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
              Something wrong in a record is a correction we want: a quote that is not in the article, a
              headline that misreads it, an outlet credited for a photograph that is not theirs. Write to{" "}
              <a className="underline underline-offset-4" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>{" "}
              with the record\u2019s link. {LEGAL_ENTITY} publishes Prism and is answerable for it.
            </p>
          </section>

          <section id="status" className="scroll-mt-24 border-t py-10 lg:py-14" style={{ borderColor: "var(--line)" }} aria-labelledby="status-title">
            <h2 id="status-title" className="font-record text-[28px] font-bold leading-[1.15] tracking-[-0.015em] lg:text-[34px]">Where Prism stands today.</h2>
            <div className="mt-6 grid gap-3 md:grid-cols-3">
              <StatusColumn tone="now" label="Available now" items={AVAILABLE} />
              <StatusColumn tone="val" label="In validation" items={VALIDATION} />
              <StatusColumn tone="next" label="Next" items={NEXT} />
            </div>
            <p className="mt-5 max-w-[64ch] text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>The record, the sources, the verified quotes and the story status are free for every reader. Professional readings, watchlists and alerts are the part of Prism that can be paid for.</p>
          </section>

          <section className="border-t py-12 text-center" style={{ borderColor: "var(--line)" }}>
            <h2 className="font-record text-[30px] font-bold leading-[1.1] tracking-[-0.015em]">Now read one for yourself.</h2>
            <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
              {event ? <Link href={`/story/${event.id}`} className="btn btn-primary btn-lg">Open the example story <ArrowRight /></Link> : <Link href="/feed" className="btn btn-primary btn-lg">Open today&rsquo;s record <ArrowRight /></Link>}
              <Link href="/onboarding" className="btn btn-ghost btn-lg">Set up my feed</Link>
            </div>
            <p className="mt-3 text-[14px]" style={{ color: "var(--ink-3)" }}>Free. No account needed to read.</p>
          </section>
        </div>
      </div>
    </div>
  );
}

/** Step 01's example: the reports as they arrived. Kept beside Step for the two-column shell. */
export function ReportsExample({ reports, outlets }: { reports: EventDetail["sources"]; outlets: OutletRef[] }) {
  if (reports.length === 0) return <Unavailable what="The reports" />;
  const idx = indexSources(reports);
  return (
    <ol className="flex flex-col gap-2.5" aria-label="The reports, oldest first">
      {reports.slice(0, 4).map((s, i) => (
        <li key={s.article_id}>
          <Reveal delay={i * 60}><ReportCard source={s} n={idx.get(s.article_id)} compact /></Reveal>
        </li>
      ))}
      {reports.length > 4 && (
        <li className="flex items-center gap-2 px-1 text-[13px]" style={{ color: "var(--ink-3)" }}>
          <span className="inline-flex -space-x-1">{reports.slice(4, 8).map((s) => <OutletIcon key={s.article_id} domain={s.domain} code={s.code ?? "?"} name={s.source_name} size={20} />)}</span>
          and {reports.length - 4} more{outlets.length ? ` from ${publishers(outlets).length} outlets` : ""}
        </li>
      )}
    </ol>
  );
}
