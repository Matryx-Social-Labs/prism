import type { Metadata } from "next";
import Link from "next/link";
import { BranchTree } from "@/components/BranchTree";
import { HeroLensDemo } from "@/components/HeroLensDemo";
import { Said } from "@/components/Said";
import { SectionHead } from "@/components/SectionHead";
import { SourceList, indexSources } from "@/components/SourceList";
import { fetchEvent, fetchFeed, fetchTrendingStory, type EventDetail, type TrendingStoryDetail } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { ticketFacts } from "@/lib/ticket";

// The pitch, moved off the front door (D5): the promise and the flip in one
// screen, then three proofs pulled LIVE from today's chart, then how it is
// made, then the tiers with the locked-lens flip as the demo. One action.
//
// Rendered per request so the proofs are today's, not the build's; the data
// calls themselves are cached for a minute like every anonymous read.
export const dynamic = "force-dynamic";

export const metadata: Metadata = {
  title: "About",
  description: "How Prism reads a story: every outlet's report of one event, gathered into one story you can re-read through a professional lens.",
};

const CTA = "Read today's chart";
const MAX_SOURCES = 6;

type Proofs = {
  route: { event: EventDetail; story: TrendingStoryDetail } | null;
  said: EventDetail | null;
  sources: EventDetail | null;
};

/**
 * Three things a visitor can check, from the chart as it stands: a route with
 * more than one development, a story with at least one verbatim quote, and the
 * most-corroborated story's sources. Nothing is invented: a proof the chart
 * cannot supply right now is simply absent.
 */
async function loadProofs(): Promise<Proofs | null> {
  try {
    const top = chartOrder(await fetchFeed({ limit: 40 })).slice(0, 8);
    const events = (await Promise.all(top.map((i) => fetchEvent(i.id).catch(() => null)))).filter(
      (e): e is EventDetail => e !== null,
    );
    let route: Proofs["route"] = null;
    for (const event of events) {
      if (!event.story_slug) continue;
      const story = await fetchTrendingStory(event.story_slug).catch(() => null);
      if (story?.branches && story.branches.nodes.length >= 2) {
        route = { event, story };
        break;
      }
    }
    return {
      route,
      said: events.find((e) => (e.claims ?? []).length > 0) ?? null,
      sources: events[0] ?? null,
    };
  } catch {
    return null;
  }
}

/** One proof row: the story it comes from at the left, the evidence at the right. */
function Proof({ title, event, children }: { title: string; event: EventDetail; children: React.ReactNode }) {
  return (
    <div className="rule-live grid gap-x-8 gap-y-4 py-7 lg:grid-cols-[280px_minmax(0,604px)]">
      <div>
        <h3 className="font-display text-[22px] font-medium uppercase leading-none tracking-[0.03em]">{title}</h3>
        <p className="mt-2 font-mono text-[10.5px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }}>
          {ticketFacts(event).slice(0, 2).join(" · ")}
        </p>
        <Link
          href={`/story/${event.id}`}
          className="mt-2 block text-[15px] font-medium leading-[1.35] underline-offset-4 hover:underline"
          style={{ color: "var(--ink)" }}
        >
          {event.title}
        </Link>
      </div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

const MADE: [string, string][] = [
  ["Gather", "Outlets across six languages are read on a schedule. Each report keeps its outlet, its time and its country of origin."],
  ["Cluster", "Reports of the same event become one story. The number of outlets that filed it is the story's weight on the chart."],
  ["Verify", "A quote is shown only if its exact words are in the article. A ticker is shown only if a listed security carries it."],
  ["Re-read", "A lens re-typesets the same record for a different reader. The facts do not change. The reading does."],
];

export default async function AboutPage() {
  const proofs = await loadProofs();

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 sm:px-8 lg:pb-20">
      {/* The promise and the flip, in one screen. */}
      <section className="grid gap-8 pt-8 lg:grid-cols-[minmax(0,1fr)_520px] lg:items-center lg:gap-14 lg:pt-14">
        <div>
          <h1 className="text-[38px] font-medium leading-[1.02] text-balance sm:text-[48px] lg:text-[56px]">
            One story. Every perspective.
          </h1>
          <p className="mt-5 max-w-[44ch] text-[16px] leading-[1.6] sm:text-[17px]" style={{ color: "var(--ink-muted)" }}>
            Every outlet&rsquo;s report of one event, gathered into one story you can re-read through a
            professional lens.
          </p>
          <Link
            href="/"
            className="mt-7 inline-flex h-12 items-center rounded-full px-6 text-[14.5px] font-semibold transition hover:opacity-85 active:translate-y-px"
            style={{ background: "var(--ink)", color: "var(--bg)" }}
          >
            {CTA}
          </Link>
        </div>
        <HeroLensDemo />
      </section>

      {/* Three proofs, live. */}
      <section className="mt-16" aria-labelledby="proofs-title">
        <SectionHead
          id="proofs-title"
          title="Three things you can check"
          hint="Pulled from today's chart as this page loaded. Every number is counted, every quote is verbatim, every source is named."
        />
        {proofs === null ? (
          <p className="py-6 text-[14.5px]" style={{ color: "var(--danger)" }}>
            The chart is unreachable right now, so there is nothing to show here yet.
          </p>
        ) : (
          <div>
            {proofs.route && (
              <Proof title="The route" event={proofs.route.event}>
                <BranchTree
                  tree={proofs.route.story.branches!}
                  developments={proofs.route.story.developments}
                  currentId={proofs.route.event.id}
                />
              </Proof>
            )}
            {proofs.said && (
              <Proof title="What was said" event={proofs.said}>
                <Said claims={proofs.said.claims ?? []} sourceIndex={indexSources(proofs.said.sources)} />
              </Proof>
            )}
            {proofs.sources && (
              <Proof title="Sources" event={proofs.sources}>
                <SourceList sources={proofs.sources.sources.slice(0, MAX_SOURCES)} sourceIndex={indexSources(proofs.sources.sources)} />
                {proofs.sources.sources.length > MAX_SOURCES && (
                  <Link
                    href={`/story/${proofs.sources.id}`}
                    className="rule-live block py-3 font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline"
                    style={{ color: "var(--ink-muted)" }}
                  >
                    All {proofs.sources.sources.length} sources on the story
                  </Link>
                )}
              </Proof>
            )}
            {!proofs.route && !proofs.said && !proofs.sources && (
              <p className="py-6 text-[14.5px]" style={{ color: "var(--ink-muted)" }}>
                Nothing on today&rsquo;s chart yet.
              </p>
            )}
          </div>
        )}
      </section>

      {/* How it is made, in plain words. */}
      <section className="mt-16" aria-labelledby="made-title">
        <SectionHead id="made-title" title="How it is made" />
        <dl>
          {MADE.map(([term, body]) => (
            <div key={term} className="rule-live grid gap-x-8 gap-y-1 py-5 sm:grid-cols-[180px_minmax(0,604px)]">
              <dt className="font-display text-[22px] font-medium uppercase leading-none tracking-[0.03em]">{term}</dt>
              <dd className="text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
                {body}
              </dd>
            </div>
          ))}
        </dl>
      </section>

      {/* The tiers, with the locked-lens flip as the demo. No pricing UI: the
          checkout does not exist yet, and this page does not pretend it does. */}
      <section className="mt-16" aria-labelledby="tiers-title">
        <SectionHead id="tiers-title" title="Free to read. Paid to read as a professional." />
        <p className="max-w-[60ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
          The Reader lens is free for everyone, with every quote and every source. The professional lenses
          are readings of the same record for people whose work depends on it. A locked lens still flips,
          so you see what you are missing before you sign in.
        </p>
        <div className="mt-6 max-w-[604px]">
          <HeroLensDemo locked={["markets", "health", "policy"]} title="Flip to a locked lens" />
        </div>
      </section>

      {/* One action. */}
      <section className="rule-live mt-16 pt-8">
        <Link
          href="/"
          className="inline-flex h-12 items-center rounded-full px-6 text-[14.5px] font-semibold transition hover:opacity-85 active:translate-y-px"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          {CTA}
        </Link>
      </section>
    </div>
  );
}
