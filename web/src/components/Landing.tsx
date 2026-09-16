import Link from "next/link";
import { BranchTree } from "@/components/BranchTree";
import { HeroLensDemo } from "@/components/HeroLensDemo";
import { LensRegistry } from "@/components/LensRegistry";
import { Said } from "@/components/Said";
import { SectionHead } from "@/components/SectionHead";
import { SourceList, indexSources } from "@/components/SourceList";
import { fetchEvent, fetchFeed, fetchTrendingStory, type EventDetail, type TrendingStoryDetail } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { ticketFacts } from "@/lib/ticket";

/**
 * The landing: `/` for a first visitor (returning readers are redirected to
 * the chart; see app/page.tsx) and `/about` always. The promise and the flip
 * in one screen, then three proofs pulled LIVE from today's chart, then how it
 * is made, then what is being built next, then the tiers with the locked-lens
 * flip as the demo. One action, and it goes to /feed: `/` would show a first
 * visitor this page again.
 *
 * Honesty rules, none of them about roadmap (founder, 2026-09-16: roadmap
 * sections stay): a proof the chart cannot supply is absent, never invented;
 * every written example says ILLUSTRATION in the provenance voice and carries
 * no invented counts; a section for a feature still being built says so under
 * its head. Lens names are never enumerated in prose; the registry renders
 * /api/v1/lenses.
 *
 * Rendered per request so the proofs are today's, not the build's; the data
 * calls themselves are cached for a minute like every anonymous read.
 */
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
      // The coaches: the story with the most named sources, and at least two —
      // a "Sources" proof with one source proves nothing.
      sources: [...events].filter((e) => e.sources.length >= 2).sort((a, b) => b.sources.length - a.sources.length)[0] ?? null,
    };
  } catch {
    return null;
  }
}

/** One proof row: the story it comes from at the left, the evidence at the right. */
function Proof({ title, event, children }: { title: string; event: EventDetail; children: React.ReactNode }) {
  return (
    <div className="rule-live grid gap-x-8 gap-y-4 py-7 lg:grid-cols-[280px_minmax(0,560px)]">
      <div>
        <h3 className="font-display text-[22px] font-medium uppercase leading-none tracking-[0.03em]">{title}</h3>
        <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }}>
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

// Worked examples for what is being built next. Written, labelled as
// illustrations, and free of counts.
const BOTH_SIDES = [
  {
    label: "Access to medicine won",
    region: "India · Global South",
    body: "Domestic and global-health outlets frame the ruling as a public-health milestone: a drug priced for the few, opened to millions.",
    sources: "The Hindu · DW (public broadcaster)",
  },
  {
    label: "Innovation undermined",
    region: "US · EU",
    body: "Industry and financial press frame it as patent erosion that will chill R&D investment in the region, and warn of trade consequences.",
    sources: "WSJ · FiercePharma",
  },
];

const CONSEQUENCES = [
  { glyph: "▲", entity: "Domestic data-centre builders", effect: "accelerated GPU procurement", horizon: "weeks" },
  { glyph: "↳", entity: "Power utilities near new capacity", effect: "grid-demand contracts reprice", horizon: "months", child: true },
  { glyph: "▼", entity: "Grey-market resellers", effect: "arbitrage window closes", horizon: "immediate" },
  { glyph: "↳", entity: "Non-allied markets", effect: "domestic accelerator programmes gain urgency", horizon: "quarters", child: true },
];

const BLINDSPOTS = [
  {
    flag: "One-sided coverage · Elections",
    title: "State assembly passes contested electoral-roll revision bill",
    note: "Every source aligned with the ruling party; the opposition's framing hasn't been picked up. Prism pulls it in and shows both.",
  },
  {
    flag: "Single-origin · Trade",
    title: "Deep-water port expansion approved on strategic shipping lane",
    note: "Every source from one origin; the rest of the region's media hasn't reported it yet.",
  },
];

const ASK = [
  { q: "Why was the vice-captain dropped?", a: "Selectors cited workload management after the IPL season [3]; two reports add a fitness-test result from the June camp [6][8]." },
  { q: "Will India win the cup?", a: null },
];

// Provenance labels in mono, sentence case: names and short facts, never costume.
const MONO = "font-mono text-[12px] tracking-[0.02em]";
const NEXT = "Being built next. The example below is written, not extracted.";

const Illustration = () => (
  <p className={MONO} style={{ color: "var(--ink-faint)" }}>Illustration · not a live story</p>
);

export async function Landing() {
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
            href="/feed"
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
            <div key={term} className="rule-live grid gap-x-8 gap-y-1 py-5 sm:grid-cols-[180px_minmax(0,560px)]">
              <dt className="font-display text-[22px] font-medium uppercase leading-none tracking-[0.03em]">{term}</dt>
              <dd className="max-w-[36em] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
                {body}
              </dd>
            </div>
          ))}
        </dl>
      </section>


      {/* What is being built next: both sides, so what, blindspots. Ask is live
          but cannot be shown live without a call, so it is written too. */}
      <section className="mt-16 grid gap-x-14 gap-y-4 lg:grid-cols-[minmax(0,1fr)_560px]" aria-labelledby="sides-title">
        <div>
          <SectionHead id="sides-title" title="The same ruling is two different stories" hint={NEXT} />
          <p className="max-w-[44ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            Prism groups a story&rsquo;s sources by stance, side by side, with every outlet&rsquo;s origin and funding
            labelled. You see every framing, <strong style={{ color: "var(--ink)" }}>and who is speaking</strong>.
          </p>
        </div>
        <div className="lg:pt-4">
          <Illustration />
          <div className="mt-2 grid gap-x-8 sm:grid-cols-2">
            {BOTH_SIDES.map((s) => (
              <div key={s.label} className="rule-live py-4">
                <p className="text-[15.5px] font-medium" style={{ color: "var(--ink)" }}>{s.label}</p>
                <p className={MONO} style={{ color: "var(--ink-faint)" }}>{s.region}</p>
                <p className="mt-2 text-[14px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>{s.body}</p>
                <p className={`${MONO} mt-3`} style={{ color: "var(--ink-faint)" }}>{s.sources}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mt-16 grid gap-x-14 gap-y-4 lg:grid-cols-[minmax(0,1fr)_560px]" aria-labelledby="sowhat-title">
        <div>
          <SectionHead id="sowhat-title" title="What happens next, spelled out" hint={NEXT} />
          <p className="max-w-[44ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            Every story carries its consequence graph: who is affected first, and the likely second-order effects,
            each with a direction and a horizon, never vague.
          </p>
        </div>
        <div className="lg:pt-4">
          <Illustration />
          <p className="rule-live mt-2 py-3 text-[15.5px] font-medium" style={{ color: "var(--ink)" }}>&ldquo;AI-chip export rules eased for allied markets&rdquo;</p>
          <ul>
            {CONSEQUENCES.map((c, i) => (
              <li key={i} className={`rule-live flex gap-3 py-3 text-[14px] leading-[1.55] ${c.child ? "ml-7" : ""}`}>
                {/* Monochrome: colour is a lens, and no lens speaks here. */}
                <span aria-hidden className="font-mono" style={{ color: "var(--ink-faint)" }}>{c.glyph}</span>
                <span>
                  <strong style={{ color: "var(--ink)" }}>{c.entity}</strong> <span style={{ color: "var(--ink-muted)" }}>· {c.effect}</span>{" "}
                  <span className={MONO} style={{ color: "var(--ink-faint)" }}>· {c.horizon}</span>
                </span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      <section className="mt-16 grid gap-x-14 gap-y-10 lg:grid-cols-2" aria-labelledby="blind-title">
        <div>
          <SectionHead id="blind-title" title="Some stories you only ever hear one way" hint={NEXT} />
          <p className="max-w-[44ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            A blindspot is any story where only one side is speaking: every source from one origin, or every outlet
            aligned with one party. Prism measures who&rsquo;s telling each story and flags what&rsquo;s missing.
          </p>
          <div className="mt-6">
            <Illustration />
            {BLINDSPOTS.map((b) => (
              <div key={b.title} className="rule-live mt-2 py-4">
                <p className={MONO} style={{ color: "var(--ink-faint)" }}>⚠ {b.flag}</p>
                <p className="mt-1.5 text-[15.5px] font-medium leading-[1.4]" style={{ color: "var(--ink)" }}>{b.title}</p>
                <p className="mt-1.5 text-[13.5px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>{b.note}</p>
              </div>
            ))}
          </div>
        </div>
        <div>
          <SectionHead id="ask-title" title="Ask anything. Get sources, or honesty" />
          <p className="max-w-[44ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            The agent answers from a story&rsquo;s own sources with citations. When they don&rsquo;t cover the
            question, it says so instead of guessing. Refusal is a feature.
          </p>
          <div className="mt-6">
            <Illustration />
            <p className="rule-live mt-2 py-3 text-[13.5px] font-medium" style={{ color: "var(--ink-muted)" }}>
              On: &ldquo;India names T20 World Cup squad: three debutants, a shock omission&rdquo;
            </p>
            <dl>
              {ASK.map((x) => (
                <div key={x.q} className="rule-live grid grid-cols-[28px_1fr] gap-x-3 py-3 text-[14px] leading-[1.6]">
                  <dt className="font-mono text-[11px] leading-[2.2]" style={{ color: "var(--ink-faint)" }}>Q</dt>
                  <dd style={{ color: "var(--ink)" }}>{x.q}</dd>
                  <dt className="font-mono text-[11px] leading-[2.2]" style={{ color: "var(--ink-faint)" }}>A</dt>
                  <dd style={{ color: "var(--ink-muted)" }}>
                    {x.a ?? (
                      <>
                        <span className={MONO} style={{ color: "var(--ink)" }}>Not in sources</span>
                        {": "}the sources for this story don&rsquo;t cover that.
                      </>
                    )}
                  </dd>
                </div>
              ))}
            </dl>
          </div>
        </div>
      </section>

      {/* The tiers, with the locked-lens flip as the demo. No pricing UI: the
          checkout does not exist yet, and this page does not pretend it does. */}
      <section className="mt-16" aria-labelledby="tiers-title">
        <SectionHead id="tiers-title" title="Free to read. Paid to read as a professional." />
        <p className="max-w-[36em] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
          The Reader lens is free for everyone, with every quote and every source. The professional lenses
          are readings of the same record for people whose work depends on it. A locked lens still flips,
          so you see what you are missing before you sign in.
        </p>
        <div className="mt-6 max-w-[560px]">
          <HeroLensDemo locked={["markets", "health", "policy"]} title="Flip to a locked lens" />
        </div>
        {/* The reads that exist today, from the registry, never a typed list. */}
        <div className="mt-8 max-w-[560px]">
          <LensRegistry />
        </div>
      </section>

      {/* One action. */}
      <section className="rule-live mt-16 pt-8">
        <Link
          href="/feed"
          className="inline-flex h-12 items-center rounded-full px-6 text-[14.5px] font-semibold transition hover:opacity-85 active:translate-y-px"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          {CTA}
        </Link>
      </section>
    </div>
  );
}
