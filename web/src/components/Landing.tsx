import Link from "next/link";
import { BranchTree } from "@/components/BranchTree";
import { ChartRow } from "@/components/ChartRow";
import { HeroLensDemo } from "@/components/HeroLensDemo";
import { LensRegistry } from "@/components/LensRegistry";
import { Said } from "@/components/Said";
import { SectionHead } from "@/components/SectionHead";
import { SectorStrip } from "@/components/SectorStrip";
import { indexSources } from "@/components/SourceList";
import { fetchEvent, fetchFeed, fetchTrendingStory, type EventDetail, type FeedItem, type TrendingStoryDetail } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { istDate } from "@/lib/dateline";

/**
 * The landing: `/` for a first visitor (returning readers are redirected to
 * the chart; see app/page.tsx) and `/about` always. A general Indian reader
 * arriving from a link or a search: what this is, why it matters, what to do,
 * in one screen; then the product itself as the proof.
 *
 * Every visual is the product: today's real chart rows with the lead's own
 * photograph, a real verbatim quote, a real route map, the live lens
 * registry, the real sector strip. General subjects only; the cyber record
 * is real news but not the first thing a general reader should meet. The one
 * written piece, the flip demo, says ILLUSTRATION. Every action goes to /feed,
 * never `/`, which would show a first visitor this page again.
 */
const CTA = "Read today's chart";
const SHELL = "mx-auto w-full max-w-[1240px] px-5 sm:px-8";

type Evidence = {
  rows: FeedItem[];
  sources: number;
  said: EventDetail | null;
  route: { event: EventDetail; story: TrendingStoryDetail } | null;
};

/**
 * Today's chart as a general reader meets it: the window, minus the cyber
 * record, most-corroborated first. Then, from the top sixteen, the first story
 * with a verbatim quote, and from the top eight the first with a route of two
 * or more developments. A proof the chart cannot supply is absent, never invented.
 */
async function loadEvidence(): Promise<Evidence | null> {
  try {
    const all = await fetchFeed({ limit: 60 });
    const rows = chartOrder(all.filter((i) => i.sector !== "cybersecurity"));
    const events = (await Promise.all(rows.slice(0, 16).map((i) => fetchEvent(i.id).catch(() => null)))).filter(
      (e): e is EventDetail => e !== null,
    );
    let route: Evidence["route"] = null;
    for (const event of events.slice(0, 8)) {
      if (!event.story_slug) continue;
      const story = await fetchTrendingStory(event.story_slug).catch(() => null);
      if (story?.branches && story.branches.nodes.length >= 2) {
        route = { event, story };
        break;
      }
    }
    return {
      rows: rows.slice(0, 4),
      sources: rows.reduce((n, i) => n + (i.source_count || 0), 0),
      said: events.find((e) => (e.claims ?? []).length > 0) ?? null,
      route,
    };
  } catch {
    return null;
  }
}

function Action({ href, children }: { href: string; children: React.ReactNode }) {
  return (
    <Link
      href={href}
      className="inline-flex h-12 items-center rounded-full px-6 text-[14.5px] font-semibold transition hover:opacity-85 active:translate-y-px"
      style={{ background: "var(--ink)", color: "var(--bg)" }}
    >
      {children}
    </Link>
  );
}

/** A cell of the feature grid: the claim, one line on it, then the product doing it. */
function Cell({ title, body, wide = false, children }: { title: string; body: string; wide?: boolean; children: React.ReactNode }) {
  return (
    <div className={`rule-live py-8 ${wide ? "lg:col-span-2" : ""}`}>
      <h3 className="font-display text-[24px] font-medium uppercase leading-none tracking-[0.03em]">{title}</h3>
      <p className="mt-2 max-w-[44ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>{body}</p>
      <div className="mt-5">{children}</div>
    </div>
  );
}

const NEXT: [string, string][] = [
  ["Both sides", "When a story splits the press, the two framings sit side by side with every outlet's origin labelled, so you see who is saying what and where they stand."],
  ["What happens next", "Who is affected first and what likely follows, each with a direction and a horizon, spelled out under the story."],
  ["Blindspots", "When every source on a story comes from one side, the story says so. You are told what you are not being told."],
];

const READER = ["Today's chart, every story, every subject", "Every quote, verbatim, with its source", "The route a story took", "Ask the story, three questions a day"];
const PRO = ["Your profession's reading of every story", "Tickers and catalysts on the stories that move markets", "CVEs, exploitation and fixes on the stories that expose you", "A watchlist of what you follow"];

export async function Landing() {
  const ev = await loadEvidence();
  const lead = ev?.rows[0] ?? null;
  const said = ev?.said ?? null;
  const dateline = ev
    ? `${istDate(new Date())}. ${ev.rows.length ? `The four most-corroborated stories on the chart, from ${ev.sources.toLocaleString("en-IN")} outlet reports.` : "Nothing on the chart yet."}`
    : "The chart is unreachable right now.";

  return (
    <div className="pb-24 lg:pb-20">
      {/* The promise and the flip, in one screen. */}
      <section className={`${SHELL} grid gap-8 pt-8 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-center lg:gap-14 lg:pt-14`}>
        <div>
          <h1 className="text-[38px] font-medium leading-[1.02] text-balance sm:text-[48px] lg:text-[56px]">
            One story. Every perspective.
          </h1>
          <p className="mt-5 max-w-[44ch] text-[16px] leading-[1.6] sm:text-[17px]" style={{ color: "var(--ink-muted)" }}>
            Every outlet&rsquo;s report of one event, gathered into one story you can check, and re-read for your work.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3">
            <Action href="/feed">{CTA}</Action>
            <a href="#what-you-get" className="text-[14.5px] font-medium underline underline-offset-4" style={{ color: "var(--ink)" }}>
              See what you get
            </a>
          </div>
        </div>
        <HeroLensDemo />
      </section>

      {/* Today's chart, the real rows, the lead with its own photograph. */}
      <section className={`${SHELL} mt-16`} aria-labelledby="chart-title">
        <SectionHead id="chart-title" title="Today's chart" hint={dateline} />
        {ev && ev.rows.length > 0 ? (
          <>
            <ol className="chart-print">
              {ev.rows.map((it, i) => <ChartRow key={it.id} item={it} lead={i === 0} />)}
            </ol>
            <Link href="/feed" className="rule-live block py-4 font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
              The whole chart →
            </Link>
          </>
        ) : (
          <p className="py-6 text-[15px]" style={{ color: ev ? "var(--ink-muted)" : "var(--danger)" }}>
            {ev ? "Nothing on today's chart yet." : "The chart is unreachable right now, so there is nothing to show here yet."}
          </p>
        )}
      </section>

      {/* What you get: each claim followed by the product doing it. */}
      <section id="what-you-get" className={`${SHELL} mt-16 scroll-mt-20`} aria-labelledby="get-title">
        <SectionHead id="get-title" title="What you get" />
        <div className="grid lg:grid-cols-2 lg:gap-x-14">
          <Cell title="One story, not fifty headlines" body="Every outlet's report of the same event is gathered into one story. The number beside it is how many outlets filed it, so you can see how much of the press agrees it happened.">
            {lead ? (
              <div className="flex items-baseline gap-4">
                <span className="font-display text-[64px] leading-[0.85] tabular-nums">{lead.source_count}</span>
                <div className="min-w-0">
                  <p className="font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-faint)" }}>outlets filed this story today</p>
                  <Link href={`/story/${lead.id}`} className="mt-1 block text-[15.5px] font-medium leading-[1.35] underline-offset-4 hover:underline">{lead.title}</Link>
                </div>
              </div>
            ) : (
              <p className="text-[14.5px]" style={{ color: "var(--ink-faint)" }}>Today&rsquo;s count appears here when the chart is reachable.</p>
            )}
          </Cell>

          <Cell title="Who said what, in their own words" body="A quote appears only when its exact words are in the article, with the outlet and the date beside it. No paraphrase, no stance we invented.">
            {said ? (
              <div>
                <Said claims={(said.claims ?? []).slice(0, 1).map((s) => ({ ...s, claims: s.claims.slice(0, 2) }))} sourceIndex={indexSources(said.sources)} />
                <Link href={`/story/${said.id}`} className="mt-3 inline-block font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
                  The story →
                </Link>
              </div>
            ) : (
              <p className="text-[14.5px]" style={{ color: "var(--ink-faint)" }}>No story on today&rsquo;s chart carries a verified quote yet.</p>
            )}
          </Cell>

          {ev?.route && (
            <Cell wide title="Follow the story as it moves" body="A story is a route: what started it, what followed, where it branched. Counted from the record, never summarised by a model.">
              <div className={ev.route.event.image_url ? "grid gap-6 lg:grid-cols-[320px_minmax(0,600px)] lg:gap-10" : "max-w-[600px]"}>
                {ev.route.event.image_url && (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={ev.route.event.image_url} alt="" className="aspect-[4/3] w-full object-cover" style={{ filter: "grayscale(0.15) contrast(1.02)" }} loading="lazy" />
                )}
                <div className="min-w-0">
                  <Link href={`/story/${ev.route.event.id}`} className="mb-3 block text-[15.5px] font-medium leading-[1.35] underline-offset-4 hover:underline">{ev.route.event.title}</Link>
                  <BranchTree tree={ev.route.story.branches!} developments={ev.route.story.developments} currentId={ev.route.event.id} />
                </div>
              </div>
            </Cell>
          )}

          <Cell title="Read it your way" body="Say what you do and every story is re-read for it: what is pulled out, how the chart ranks, what the agent asks. The Reader lens is free; professional reads are one tap away.">
            <LensRegistry />
          </Cell>

          <Cell title="Ask the story, get sources" body="Ask anything about a story. The answer cites the story's own sources, or says it cannot. Refusal is a feature.">
            <p className="font-mono text-[12px]" style={{ color: "var(--ink-faint)" }}>Illustration</p>
            <dl className="max-w-[44ch]">
              {[
                ["Why was the order rushed before winter?", "The transport minister cited the November smog forecast [2]; two outlets add a pending court deadline [4][5]."],
                ["Will Mumbai follow?", null],
              ].map(([q, a]) => (
                <div key={q as string} className="rule-live mt-2 grid grid-cols-[20px_1fr] gap-x-2 py-3 text-[14.5px] leading-[1.6]">
                  <dt className="font-mono text-[11px] leading-[2.2]" style={{ color: "var(--ink-faint)" }}>Q</dt>
                  <dd style={{ color: "var(--ink)" }}>{q}</dd>
                  <dt className="font-mono text-[11px] leading-[2.2]" style={{ color: "var(--ink-faint)" }}>A</dt>
                  <dd style={{ color: "var(--ink-muted)" }}>
                    {a ?? (
                      <>
                        <span className="font-mono text-[11px]" style={{ color: "var(--ink)" }}>Not in sources.</span> The sources for this story don&rsquo;t cover that.
                      </>
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </Cell>

          <Cell wide title="Six subjects, your state first" body="Politics to entertainment on one strip, on every page. Tell us your state and its news leads the chart; follow a subject and For you appears.">
            <div className="[&_nav]:static [&_nav]:border-b-0">
              <SectorStrip active={null} allHref="/feed" allLabel="Today" />
            </div>
          </Cell>
        </div>
      </section>

      {/* Being built next: named, in one line each, no invented examples. */}
      <section className={`${SHELL} mt-16`} aria-labelledby="next-title">
        <SectionHead id="next-title" title="Being built next" />
        <div className="grid gap-x-14 lg:grid-cols-3">
          {NEXT.map(([title, body]) => (
            <div key={title} className="rule-live py-6">
              <h3 className="font-display text-[22px] font-medium uppercase leading-none tracking-[0.03em]">{title}</h3>
              <p className="mt-2 text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      {/* The tiers. No pricing UI: the checkout does not exist yet and this page does not pretend it does. */}
      <section className={`${SHELL} mt-16`} aria-labelledby="tiers-title">
        <SectionHead id="tiers-title" title="Free to read. Paid to read as a professional." />
        <div className="grid gap-x-14 lg:grid-cols-2">
          {[["Reader", "Free, no account needed", READER], ["Professional reads", "For people whose work depends on the news", PRO]].map(([name, sub, items]) => (
            <div key={name as string} className="rule-live py-6">
              <h3 className="font-display text-[22px] font-medium uppercase leading-none tracking-[0.03em]">{name}</h3>
              <p className="mt-1.5 text-[14px]" style={{ color: "var(--ink-muted)" }}>{sub}</p>
              <ul className="mt-4 flex flex-col gap-2.5">
                {(items as string[]).map((line) => (
                  <li key={line} className="flex gap-3 text-[15px] leading-[1.5]">
                    <span aria-hidden className="mt-[11px] inline-block h-[2px] w-3 shrink-0" style={{ background: "var(--ink)" }} />
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      </section>

      {/* One action. */}
      <section className={`${SHELL} rule-live mt-16 flex flex-wrap items-center gap-x-6 gap-y-3 pt-8`}>
        <Action href="/feed">{CTA}</Action>
        <Link href="/onboarding" className="text-[14.5px] font-medium underline underline-offset-4" style={{ color: "var(--ink)" }}>
          Pick your sectors
        </Link>
      </section>
    </div>
  );
}
