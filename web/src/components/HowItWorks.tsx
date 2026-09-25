import Link from "next/link";
import { CoverageBar, CoverageLegend, MonogramStack, OutletIcon } from "@/components/Coverage";
import { EntityText } from "@/components/EntityText";
import { LensRegistry } from "@/components/LensRegistry";
import { ReportCard } from "@/components/SourceList";
import { ReportProblem } from "@/components/ReportProblem";
import { Reveal } from "@/components/Reveal";
import { Said } from "@/components/Said";
import { StepRail } from "@/components/StepRail";
import { FREE_LINE, StatusColumns } from "@/components/StatusGrid";
import { LensFlip } from "@/components/landing/LensFlip";
import { LiveLead, outletsOf } from "@/components/landing/parts";
import { fetchEvent, fetchFeed, fetchQuestions, type EventDetail, type FeedItem, type OutletRef } from "@/lib/api";
import { coverageText, languageNames, languagesOf, publishers } from "@/lib/coverage";
import { CONTACT_EMAIL, LEGAL_ENTITY } from "@/lib/legal";
import { sentences } from "@/lib/sentences";
import { indexSources } from "@/lib/sources";
import { Ago } from "@/components/Ago";

/**
 * How Prism works (/about): one real story from today's record, followed
 * through the product step by step: the reports as they came in, the one
 * record they became, who covered it, who said what, the brief written from
 * them, the same facts read through a lens, and the question box. Every
 * example is live and counted; nothing is written for the page. Then what
 * Prism refuses to do, where it stands, and the door in. Built from the
 * landing's sections and the system's classes (Design System v2); steps print
 * in as they are reached (Reveal), and reduced motion shows them.
 */
const STEPS = [
  { id: "reports", n: "01", label: "Reports come in" },
  { id: "record", n: "02", label: "One record" },
  { id: "coverage", n: "03", label: "Who covered it" },
  { id: "said", n: "04", label: "Who said what" },
  { id: "brief", n: "05", label: "The brief" },
  { id: "lens", n: "06", label: "Read it through a lens" },
  { id: "ask", n: "07", label: "Ask the record" },
  { id: "refuses", n: "08", label: "What Prism refuses" },
  { id: "words", n: "09", label: "The words it uses" },
  { id: "accountability", n: "10", label: "Who answers for it" },
];

const REFUSALS: [string, string][] = [
  ["No invented numbers.", "Every count on a page is counted from the reports: outlets, languages, quotes, developments. If it is not countable, it is not printed."],
  ["No count without its denominator.", "\u201C2 outlets\u201D means 2 of the outlets Prism monitors, never everyone who covered the story. The list of them is public, with when each was last read."],
  ["No quote that is not in the article.", "A quote appears only when the same words are in the article it came from. When the check fails the quote is dropped, never paraphrased."],
  ["No guess presented as a fact.", "The brief restates the reports. Where it says why something matters, that is Prism\u2019s reading, and the page says so."],
  ["No left, right or centre.", "Coverage is described by where an outlet comes from, a fact of the source. Prism rates neither an outlet\u2019s politics nor a report\u2019s tone: nobody has made those ratings for Indian outlets, and a machine\u2019s guess is not one."],
  ["No photos of its own.", "A picture is only ever the outlet's, shown as a credited link preview of that outlet's report, never as Prism's."],
  ["No silent edits.", "Every record shows when it was last updated and keeps every earlier version; a correction says what was wrong and why."],
];

// The words a record uses, for a reader meeting them for the first time. Plain
// definitions, in the order a record shows them.
const WORDS: [string, string][] = [
  ["Report", "One article by one outlet, kept as it was published, with its outlet and time. Prism links to it; the journalism is the outlet\u2019s."],
  ["Record", "Everything Prism holds on one story: the reports, who said what, who covered it, and the brief written from them."],
  ["Monitored outlets", "The fixed list of outlets Prism reads. Every count on a record is out of this list."],
  ["Single source", "Only one monitored outlet has the story so far. It may be right; nobody else has confirmed it yet."],
  ["Coverage", "Which kinds of outlet carry the story: English national, Indian-language, international or wire."],
  ["Prism\u2019s reading", "A line the software wrote about what the reports mean, such as why a story matters. It is not something an outlet reported."],
  ["Lens", "The same record read for a kind of work. The facts underneath never change; only the reading does."],
];

// Editorial accountability, in the vocabulary a reader and a policy review
// both read: who writes a record, what a machine does and does not decide, and
// where a mistake goes. Bylines read "Headline by Prism" — this is the page
// that says what that means.
const ACCOUNTABILITY: [string, string][] = [
  ["A record is written by machine, and says so.", "Every headline, brief and summary on Prism is written by software from the reports listed under it, never by a journalist and never presented as one. That is why a record is bylined \u201CHeadline by Prism\u201D and names the reports it was written from."],
  ["The reporting is the outlets\u2019.", "Prism does not report. It reads what registered outlets published, keeps each report as it was, and links to it. The journalism belongs to the outlet that did it. What Prism adds is the grouping, the counts and the reading."],
  ["A quote is the article\u2019s words or it is not there.", "Quotes are checked against the article they came from before they appear. When a check fails the quote is dropped rather than paraphrased."],
  ["A correction is public.", "A record that was wrong is fixed and says so, with the date, the reason and what was wrong, and every correction is listed on the corrections page. Every earlier version of a record is kept and can be opened on it."],
];

type Example = { row: FeedItem; event: EventDetail; outlets: OutletRef[] };

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
    <section id={id} className="grid scroll-mt-24 gap-6 border-t py-10 lg:grid-cols-[minmax(0,0.85fr)_minmax(0,1.15fr)] lg:gap-12 lg:py-14" style={{ borderColor: "var(--line)" }} aria-labelledby={`${id}-title`}>
      <div className="min-w-0">
        <p className="p-eyebrow">Step {n}</p>
        <h2 id={`${id}-title`} className="mt-2" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>{title}</h2>
        <div className="mt-3 flex max-w-[46ch] flex-col gap-3" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>{children}</div>
        <p className="mt-4 max-w-[46ch] border-l-2 pl-3" style={{ borderColor: "var(--ink)", font: "var(--t-body-s)", color: "var(--ink)" }}>
          <span className="font-semibold">The rule: </span>{rule}
        </p>
      </div>
      <Reveal className="min-w-0">{example}</Reveal>
    </section>
  );
}

function Unavailable({ what }: { what: string }) {
  return <p className="p-card" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>{what} is not available in the current window.</p>;
}

/** A closing section with its own head (08 to 10, status): the landing's hairline-and-display-m shape. */
function Closing({ id, n, title, children }: { id: string; n?: string; title: string; children: React.ReactNode }) {
  return (
    <section id={id} className="scroll-mt-24 border-t py-10 lg:py-14" style={{ borderColor: "var(--line)" }} aria-labelledby={`${id}-title`}>
      {n && <p className="p-eyebrow">Step {n}</p>}
      <h2 id={`${id}-title`} className={n ? "mt-2" : ""} style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>{title}</h2>
      {children}
    </section>
  );
}

/** Heads and bodies on top rules, two columns on a desk: refusals, accountability. */
function RuledList({ items }: { items: [string, string][] }) {
  return (
    <ul className="mt-6 grid gap-x-10 gap-y-5 md:grid-cols-2">
      {items.map(([head, body], i) => (
        <li key={head} className="border-t pt-4" style={{ borderColor: "var(--line)" }}>
          <Reveal delay={i * 40}>
            <p style={{ font: "var(--t-title)" }}>{head}</p>
            <p className="mt-1.5" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{body}</p>
          </Reveal>
        </li>
      ))}
    </ul>
  );
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
  const questions = event ? await fetchQuestions(event.id).catch(() => [] as string[]) : [];

  return (
    <div className="pb-20">
      {/* ── The walk-through's opening: what it is, on which story ── */}
      <section className="sc-shell grid items-center gap-8 pb-9 pt-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-16 lg:pb-14 lg:pt-[72px]">
        <div className="min-w-0">
          <h1 className="max-w-[16ch] text-balance" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>How Prism works</h1>
          <p className="mt-3 max-w-[46ch]" style={{ font: "var(--t-body-l)", color: "var(--ink-2)" }}>
            Prism reads the day&rsquo;s reports from the outlets it monitors and keeps one record per story: what each outlet reported, who said what in their exact words, and a brief written only from those reports. Below, one story from today&rsquo;s record goes through it, step by step.
          </p>
          <div className="mt-[22px] flex flex-col gap-2.5 lg:flex-row">
            <a href="#reports" className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto">Start with the reports</a>
            <Link href="/feed" className="p-btn p-btn--secondary p-btn--lg w-full lg:w-auto">Open today&rsquo;s record</Link>
          </div>
        </div>
        <Reveal delay={120} className="min-w-0">
          {ex ? (
            <div className="p-card" style={{ borderTop: "var(--rule-section) solid var(--ink)" }}>
              <p className="p-eyebrow">Today&rsquo;s example</p>
              <Link href={`/story/${event!.id}`} className="mt-2 block text-balance underline-offset-4 hover:underline" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>{event!.title}</Link>
              <p className="p-count mt-2 whitespace-normal">
                {coverageText(outlets, event!.sources.length)} · {event!.sources.length} {event!.sources.length === 1 ? "report" : "reports"}{langs.length ? ` · ${languageNames(langs)}` : ""} · updated <Ago iso={event!.last_updated_at} />
              </p>
            </div>
          ) : (
            <div className="p-card" role="status">
              <p style={{ font: "var(--t-title)" }}>The live record is unavailable right now.</p>
              <p className="mt-2" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>The steps below still explain how it works; the examples return when the monitored feed reconnects.</p>
            </div>
          )}
        </Reveal>
      </section>

      <div className="sc-shell lg:grid lg:grid-cols-[var(--rail)_minmax(0,1fr)] lg:gap-x-10">
        <StepRail steps={STEPS} />
        <div className="min-w-0">
          <Step id="reports" n="01" title="Reports come in, and stay as they were." rule="A report is kept as published, with its outlet and time."
            example={<ReportsExample reports={reports} outlets={outlets} />}>
            <p>Prism watches a fixed, <Link href="/sources" className="p-link">public list of outlets</Link>: English national papers, Indian-language papers, the international press and the wires. Every report keeps its own headline, its outlet and the minute it published.</p>
            {event && <p>This story arrived as {event.sources.length} {event.sources.length === 1 ? "report" : "reports"} from {publishers(outlets).length || event.sources.length} {publishers(outlets).length === 1 ? "outlet" : "outlets"}{langs.length > 1 ? ` in ${langs.length} languages` : ""}.</p>}
          </Step>

          <Step id="record" n="02" title="Many reports become one record." rule="One row per story; the counts are counted, never typed."
            example={ex ? <LiveLead row={ex.row} outlets={outlets} /> : <Unavailable what="A live row" />}>
            <p>Reports of the same happening are matched into one record. The row you see on Today carries a headline written from the reports (or the first report&rsquo;s own), the outlets behind it, and a coverage bar. Open it and every report is one tap away.</p>
          </Step>

          <Step id="coverage" n="03" title="See who covered it, not who to trust." rule="By outlet origin, a fact of the source. Never left, right or centre."
            example={outlets.length > 0 ? (
              <div className="p-card grid gap-3">
                <div className="flex flex-wrap items-center gap-3">
                  <MonogramStack outlets={outlets} limit={6} />
                  <CoverageBar outlets={outlets} size="lg" width={220} draw className="max-w-full" />
                  <span className="p-count">{coverageText(outlets)}</span>
                </div>
                <CoverageLegend outlets={outlets} />
                <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>{publishers(outlets).map((o) => o.name).join(" · ")}</p>
              </div>
            ) : <Unavailable what="Coverage" />}>
            <p>The bar splits the reporting by where each outlet comes from: English national, Indian-language, international, wire. It answers &ldquo;who has this story?&rdquo; at a glance. The count beside it is out of the outlets Prism monitors, and a story only one of them carries is drawn dashed and marked <em>not yet corroborated</em>.</p>
            <p>No Indian outlet has an agreed left/right rating, so Prism does not invent one, and it does not label a report&rsquo;s tone either.</p>
          </Step>

          <Step id="said" n="04" title="Who said what, in their exact words." rule="Verbatim or absent. Every quote links to the line in the article."
            example={event && quote ? (
              <Said claims={[{ ...quote, claims: quote.claims.slice(0, 2) }]} sourceIndex={indexSources(event.sources)} />
            ) : <Unavailable what="A verified quote" />}>
            <p>Prism pulls out what named people and bodies said, and keeps a quote only if the same words are in the article. Each one names the speaker and their office as the article gave it, the outlet that carried it, and opens the article at that line.</p>
            {quote?.role && <p>Here: {quote.speaker}, {quote.role}.</p>}
          </Step>

          <Step id="brief" n="05" title="A brief written from the reports below it." rule="Written by software from the reports. Why it matters is Prism's reading."
            example={event && points.length > 0 ? (
              <div className="grid gap-3" style={{ borderTop: "2px solid var(--ink)", background: "var(--surface)", padding: "14px 18px 18px", borderRadius: "0 0 var(--r-lg) var(--r-lg)" }}>
                <p className="flex flex-wrap items-center gap-x-2 gap-y-1">
                  <span className="text-[13px] font-semibold">The brief</span>
                  <span className="p-count ml-auto">{event.sources.length} {event.sources.length === 1 ? "report" : "reports"}</span>
                </p>
                <ul className="grid gap-2.5" style={{ font: "var(--t-body)" }}>
                  {points.slice(0, 5).map((p, i) => (
                    <li key={i} className="grid grid-cols-[14px_1fr] gap-x-2">
                      <span aria-hidden className="mt-[11px] h-1.5 w-1.5" style={{ background: "var(--ink)" }} />
                      <EntityText text={p} entities={event.entities} claims={event.claims ?? []} />
                    </li>
                  ))}
                </ul>
                {watch.length > 0 && <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>What to watch: {watch[0]}</p>}
              </div>
            ) : <Unavailable what="A brief" />}>
            <p>Each point is one fact from the reports, written to stand on its own. The last says why it matters: that one is Prism&rsquo;s reading of the reports, not something an outlet reported. Underlined names are the people and bodies in the story: hover or tap one for who they are and what they said here.</p>
          </Step>

          <Step id="lens" n="06" title="Read the same facts for your work." rule="The record never changes. Only the reading does."
            example={event && brief ? (
              <LensFlip story={{ id: event.id, title: event.title, reports: event.sources.length, brief, points: watch, available: event.available_lenses ?? [] }} />
            ) : <Unavailable what="A brief to read through a lens" />}>
            <p>A lens is a professional reading of the record: what a story means for markets, or for security teams. Flip it and a scan line re-inks the block; the facts beneath stay exactly where they were.</p>
            <div className="mt-1"><LensRegistry /></div>
          </Step>

          <Step id="ask" n="07" title="Ask, and the answer cites the reports." rule="An answer names its sources or says it cannot tell."
            example={event ? (
              <div className="p-card grid justify-items-start gap-3">
                <p style={{ font: "var(--t-title-s)" }}>Ask this story</p>
                {questions.length > 0 && (
                  <>
                    <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>The questions its page suggests:</p>
                    <ul className="flex flex-wrap gap-1.5" aria-label="Suggested questions">
                      {questions.map((q) => <li key={q} className="p-chip p-chip--q">{q}</li>)}
                    </ul>
                  </>
                )}
                <Link href={`/story/${event.id}`} className="p-btn p-btn--secondary">Ask on the story</Link>
              </div>
            ) : <Unavailable what="A story to ask" />}>
            <p>Every record has a question box. The answer is written only from that story&rsquo;s own reports and cites them by number; when the reports do not say, it says so instead of guessing.</p>
          </Step>

          <Closing id="refuses" n="08" title="What Prism refuses to do.">
            <RuledList items={REFUSALS} />
          </Closing>

          <Closing id="words" n="09" title="The words on a record.">
            <dl className="mt-6 grid gap-x-10 md:grid-cols-2">
              {WORDS.map(([term, meaning]) => (
                <div key={term} className="border-t py-4" style={{ borderColor: "var(--line)" }}>
                  <dt style={{ font: "var(--t-title)" }}>{term}</dt>
                  <dd className="mt-1" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{meaning}</dd>
                </div>
              ))}
            </dl>
          </Closing>

          {/* The address `correctionsPolicy` and `publishingPrinciples` point at
              (lib/seo.ts): a machine-written byline is exactly what a news
              policy review reads a page like this to understand. */}
          <Closing id="accountability" n="10" title="Who writes this, and how to correct it.">
            <RuledList items={ACCOUNTABILITY} />
            <p className="mt-5 max-w-[64ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>
              Something wrong in a record is a correction we want: a quote that is not in the article, a
              headline that misreads it, an outlet credited for a photograph that is not theirs. Every record
              has these links at its foot, with its address filled in; or write to{" "}
              <a className="p-link" href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>{" "}
              with the record&rsquo;s link. {LEGAL_ENTITY} publishes Prism and is answerable for it.
            </p>
            <div className="mt-4 max-w-[420px]"><ReportProblem /></div>
          </Closing>

          <Closing id="status" title="Where Prism stands today.">
            <StatusColumns />
            <p className="mt-6 max-w-[64ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{FREE_LINE}</p>
          </Closing>

          <section className="grid justify-items-start gap-3.5 border-t pb-6 pt-12" style={{ borderColor: "var(--line)" }} aria-labelledby="final-title">
            <h2 id="final-title" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>Now read one for yourself.</h2>
            <div className="flex flex-wrap gap-2.5">
              {event ? <Link href={`/story/${event.id}`} className="p-btn p-btn--primary p-btn--lg">Open the example story</Link> : <Link href="/feed" className="p-btn p-btn--primary p-btn--lg">Open today&rsquo;s record</Link>}
              <Link href="/onboarding" className="p-btn p-btn--secondary p-btn--lg">Set up my feed</Link>
            </div>
            <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>Free. No account needed to read.</p>
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
        <li className="flex items-center gap-2 px-1" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          <span className="inline-flex -space-x-1">{reports.slice(4, 8).map((s) => <OutletIcon key={s.article_id} domain={s.domain} code={s.code ?? "?"} name={s.source_name} size={20} />)}</span>
          and {reports.length - 4} more{outlets.length ? ` from ${publishers(outlets).length} outlets` : ""}
        </li>
      )}
    </ol>
  );
}
