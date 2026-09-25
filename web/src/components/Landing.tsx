import Link from "next/link";
import { CoverageBar, CoverageLegend, MonogramStack } from "@/components/Coverage";
import { LensRegistry } from "@/components/LensRegistry";
import { Reveal } from "@/components/Reveal";
import { RouteMap } from "@/components/RouteMap";
import { Said } from "@/components/Said";
import { StoryCard } from "@/components/StoryCard";
import { PlanCards, StatusColumns } from "@/components/StatusGrid";
import { ArrowRight } from "@/components/icons";
import { IndicName } from "@/components/landing/IndicName";
import { LensFlip, type LensStory } from "@/components/landing/LensFlip";
import { ProofTabs } from "@/components/landing/ProofTabs";
import { ChangeTimeline, LiveLead, LiveUnavailable, outletsOf } from "@/components/landing/parts";
import {
  fetchEvent,
  fetchFeed,
  fetchSources,
  fetchTrendingStory,
  type EventDetail,
  type FeedItem,
  type TrendingStoryDetail,
} from "@/lib/api";
import { fetchPlans, rupees } from "@/lib/billing";
import { chartOrder } from "@/lib/chart";
import { coverageText, monitoredText, publishers } from "@/lib/coverage";
import { indexSources } from "@/lib/sources";
import { spanDays, spineLength } from "@/lib/spine";
import { Ago } from "@/components/Ago";

/**
 * The landing (Design System v2 · screens/LandingPage, "Pages v3"): a product
 * page built from the product's own components on today's record. The promise
 * beside the live lead row; the record, not a verdict, on one real story (what
 * changed, a verified quote, who covered it); four more live stories; the route
 * of a verified developing story; the lens flip on a real brief; what is live,
 * validated and next; one final call. Nothing here is written for the page:
 * every headline, count, quote, brief and route comes from the API, and a
 * section whose data is missing is left out rather than filled in.
 */
const CTA = "Open today’s record";

type Evidence = {
  rows: FeedItem[];
  lead: EventDetail | null;
  /** The one story the proof cards are built from. */
  proof: EventDetail | null;
  lens: EventDetail | null;
  route: { event: EventDetail; story: TrendingStoryDetail } | null;
  outlets: number;
  languages: number;
  /** Outlets Prism monitors: the denominator every count on the page is out of. */
  monitored: number | null;
  /** Languages of the monitored feeds, for the name in each script Prism reads. */
  monitoredLanguages: string[] | null;
};

async function loadEvidence(): Promise<Evidence | null> {
  try {
    const [all, monitored] = await Promise.all([fetchFeed({ limit: 60 }), fetchSources()]);
    const rows = chartOrder(all.filter((item) => item.sector !== "cybersecurity"));
    const events = (
      await Promise.all(rows.slice(0, 16).map((item) => fetchEvent(item.id).catch(() => null)))
    ).filter((event): event is EventDetail => event !== null);

    let route: Evidence["route"] = null;
    for (const event of events.slice(0, 8)) {
      if (!event.story_slug) continue;
      const story = await fetchTrendingStory(event.story_slug).catch(() => null);
      if (story?.boundary_status === "verified" && story.branches && spineLength(story.branches) >= 3) {
        route = { event, story };
        break;
      }
    }
    const quoted = (e: EventDetail) => (e.claims ?? []).length > 0;
    const briefed = (e: EventDetail) => Boolean(e.lens_briefs?.reader);
    // Counted from the window, never typed: distinct mastheads and languages
    // across every row that carries outlet facts.
    const outletRefs = all.flatMap((i) => i.outlets ?? []);
    const lead = events.find((e) => e.id === rows[0]?.id) ?? null;
    return {
      rows: rows.slice(0, 12),
      lead,
      proof: events.find((e) => quoted(e) && e.sources.length >= 3) ?? events.find(quoted) ?? lead,
      lens: events.find((e) => briefed(e) && (e.available_lenses ?? []).length > 1) ?? events.find(briefed) ?? null,
      route,
      outlets: new Set(outletRefs.map((o) => o.publisher)).size,
      languages: new Set(outletRefs.map((o) => o.language ?? "en")).size,
      monitored: monitored?.outlets ?? null,
      monitoredLanguages: monitored ? [...new Set(monitored.feeds.map((f) => f.language ?? "en"))] : null,
    };
  } catch {
    return null;
  }
}

/** "₹149": the cheapest monthly plan the pricing source offers, or nothing. */
async function plusFrom(): Promise<string | null> {
  const plans = await fetchPlans().catch(() => null);
  const monthly = (plans?.plans ?? []).filter((p) => p.period === "month").sort((a, b) => a.amount_paise - b.amount_paise)[0];
  return monthly ? rupees(monthly.amount_paise) : null;
}

export async function Landing() {
  const [evidence, price] = await Promise.all([loadEvidence(), plusFrom()]);
  const leadRow = evidence?.rows[0] ?? null;

  return (
    <div>
      <Hero evidence={evidence} leadRow={leadRow} />
      {evidence?.proof && <Proof event={evidence.proof} monitored={evidence.monitored} />}
      <LiveNow evidence={evidence} />
      {evidence?.route && <Unfolded route={evidence.route} />}
      <Signature event={evidence?.lens ?? null} />

      {/* ── Honest about what's live ──────────────────────────────── */}
      <section id="status" className="sc-shell scroll-mt-20 pb-10 pt-16" aria-labelledby="status-title">
        <Reveal><h2 id="status-title" style={{ font: "var(--t-display-m)" }}>Honest about what&rsquo;s live</h2></Reveal>
        <StatusColumns />
        <Reveal delay={120}><PlanCards plusFrom={price} /></Reveal>
      </section>

      {/* ── One final call ────────────────────────────────────────── */}
      <section className="sc-shell grid justify-items-start gap-3.5 pb-[72px] pt-12" aria-labelledby="final-title">
        <Reveal><h2 id="final-title" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>Open today&rsquo;s record</h2></Reveal>
        <div className="flex flex-wrap gap-2.5">
          <Link href="/feed" className="p-btn p-btn--primary p-btn--lg">Read today</Link>
          <Link href="/onboarding" className="p-btn p-btn--secondary p-btn--lg">Set up my feed</Link>
        </div>
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>Free. No account needed to read.</p>
      </section>
    </div>
  );
}

/* ── The promise, the name in every script, the live record ─────── */
function Hero({ evidence, leadRow }: { evidence: Evidence | null; leadRow: FeedItem | null }) {
  const figures: [string, string][] = evidence && evidence.outlets > 0
    ? [
        [String(evidence.outlets), evidence.monitored && evidence.monitored >= evidence.outlets ? `of ${evidence.monitored} monitored outlets in today's record` : "outlets in today's record"],
        [String(evidence.languages), evidence.languages === 1 ? "language read" : "languages read"],
        ["1", "record per story"],
      ]
    : [];
  return (
    <section className="sc-shell grid items-center gap-8 pb-9 pt-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] lg:gap-16 lg:pb-14 lg:pt-[72px]">
      <div className="min-w-0">
        <p className="p-eyebrow" style={{ color: "var(--accent)" }}>The live record · India</p>
        <div className="mt-3.5"><IndicName languages={evidence?.monitoredLanguages ?? null} /></div>
        <h1 className="mt-[18px] max-w-[16ch] text-balance" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>Follow the story, not the headlines.</h1>
        <p className="mt-3 max-w-[44ch]" style={{ font: "var(--t-body-l)", color: "var(--ink-2)" }}>
          Prism assembles each story once from the outlets it monitors and keeps the evidence attached: every report, the exact words said, which outlets covered it and how many have not yet.
        </p>
        <div className="mt-[22px] flex flex-col gap-2.5 lg:flex-row">
          <Link href="/feed" className="p-btn p-btn--primary p-btn--lg w-full lg:w-auto">{CTA}</Link>
          <a href={evidence?.proof ? "#how" : "/about"} className="p-btn p-btn--secondary p-btn--lg w-full lg:w-auto">How it works</a>
        </div>
        {figures.length > 0 && (
          <dl className="mt-7 grid grid-cols-[repeat(3,minmax(0,max-content))] gap-[18px] lg:gap-10">
            {figures.map(([n, label], i) => (
              <Reveal key={label} delay={i * 80}>
                <dt className="text-[30px] font-semibold leading-none lg:text-[40px]" style={{ fontFamily: "var(--font-record)" }}>{n}</dt>
                <dd className="mt-1.5 max-w-[16ch] text-[13px] font-medium leading-[1.3]" style={{ color: "var(--ink-3)" }}>{label}</dd>
              </Reveal>
            ))}
          </dl>
        )}
      </div>
      <Reveal delay={120} className="min-w-0">
        {leadRow ? <LiveLead row={leadRow} outlets={outletsOf(evidence?.lead ?? null)} /> : <LiveUnavailable />}
      </Reveal>
    </section>
  );
}

/* ── The record, not a verdict: three things on ONE real story ──── */
function Proof({ event, monitored }: { event: EventDetail; monitored: number | null }) {
  const outlets = outletsOf(event);
  const quote = event.claims?.[0] ?? null;
  const panels = [
    { key: "changed", title: "What changed", desc: "The three newest reports, newest first.", body: <ChangeTimeline event={event} /> },
    quote && {
      key: "said",
      title: "Exact words, exact source",
      desc: "Verbatim, with a link to the line.",
      body: (
        <>
          <Said claims={[{ ...quote, claims: quote.claims.slice(0, 1) }]} sourceIndex={indexSources(event.sources)} />
          <Link href={`/story/${event.id}#said`} className="p-btn p-btn--text -ml-1 text-[13.5px]">Every verified quote on this story</Link>
        </>
      ),
    },
    outlets.length > 0 && {
      key: "covered",
      title: "Who covered it",
      desc: "Counted by where each outlet comes from.",
      body: (
        <div className="grid gap-3">
          <div className="flex flex-wrap items-center gap-3">
            <CoverageBar outlets={outlets} size="lg" width={260} draw className="max-w-full" />
            <span className="p-count">{coverageText(outlets)}</span>
          </div>
          <p className="p-count">
            <Link href="/sources" className="underline-offset-4 hover:underline">{monitoredText(publishers(outlets).length, event.monitored_outlets ?? monitored)}</Link>
            {event.monitored_checked_at && <> · checked <Ago iso={event.monitored_checked_at} /></>}
          </p>
          <CoverageLegend outlets={outlets} />
          <MonogramStack outlets={outlets} limit={5} />
        </div>
      ),
    },
  ].filter((p): p is { key: string; title: string; desc: string; body: React.ReactElement } => Boolean(p));
  return (
    <section id="how" className="scroll-mt-20 border-y" style={{ background: "var(--surface)", borderColor: "var(--line)" }} aria-labelledby="proof-title">
      <div className="sc-shell py-14">
        <Reveal>
          <p className="p-eyebrow">What you get on every story</p>
          <h2 id="proof-title" className="mt-2" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>The record, not a verdict.</h2>
          <p className="mt-2 max-w-[60ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
            Shown on one story from today&rsquo;s record: <Link href={`/story/${event.id}`} className="p-link">{event.title}</Link>
          </p>
        </Reveal>
        <ProofTabs panels={panels} />
      </div>
    </section>
  );
}

/* ── Live now: the next four stories on the record ───────────────── */
function LiveNow({ evidence }: { evidence: Evidence | null }) {
  // The next stories on the record, the ones with a credited photograph first:
  // a card is a picture and a headline (screens/Cards.jsx).
  const next = evidence?.rows.slice(1) ?? [];
  const live = [...next.filter((r) => r.image_url), ...next.filter((r) => !r.image_url)].slice(0, 4);
  return (
    <section className="sc-shell pb-6 pt-14" aria-labelledby="live-title">
      <Reveal>
        <div className="flex items-baseline gap-3">
          <h2 id="live-title" className="flex-1" style={{ font: "var(--t-display-m)" }}>Live now</h2>
          <Link href="/feed" className="p-link inline-flex min-h-[44px] items-center gap-1 text-[14.5px]">All of today <ArrowRight size={14} /></Link>
        </div>
      </Reveal>
      {live.length > 0 ? (
        <div className="sc-rail mt-3 lg:mx-0 lg:mt-4 lg:grid lg:grid-cols-4 lg:gap-3.5 lg:overflow-visible lg:p-0">
          {live.map((item, i) => (
            <Reveal key={item.id} delay={i * 70} className="grid w-[272px] lg:w-auto">
              <StoryCard item={item} width="100%" />
            </Reveal>
          ))}
        </div>
      ) : (
        <p className="p-card mt-3" style={{ font: "var(--t-body)", color: evidence ? "var(--ink-2)" : "var(--danger)" }}>
          {evidence ? "Nothing else is on today’s record yet." : "The live record cannot be reached right now."}
        </p>
      )}
    </section>
  );
}

/* ── See what changed: a verified developing story as a route ────── */
function Unfolded({ route }: { route: { event: EventDetail; story: TrendingStoryDetail } }) {
  const { event, story } = route;
  const devs = story.branches!.shape.developments;
  const days = spanDays(story.developments);
  const title = `One story, ${devs} ${devs === 1 ? "development" : "developments"}${days ? `, ${days} ${days === 1 ? "day" : "days"}` : ""}.`;
  return (
    <section className="sc-shell py-10" aria-labelledby="route-title">
      <Reveal>
        <p className="p-eyebrow">See what changed</p>
        <h2 id="route-title" className="mt-2" style={{ font: "var(--t-display-m)" }}>{title}</h2>
        <p className="mt-1.5 max-w-[60ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          <Link href={`/story/${event.id}`} className="p-link">{event.title}</Link>
        </p>
      </Reveal>
      <Reveal delay={100} className="mt-[18px] min-w-0">
        <RouteMap tree={story.branches!} developments={story.developments} currentId={event.id} />
      </Reveal>
    </section>
  );
}

/* ── The signature: the lens flip on a real brief, in the dark ───── */
function Signature({ event }: { event: EventDetail | null }) {
  const story: LensStory | null = event?.lens_briefs?.reader
    ? { id: event.id, title: event.title, reports: event.sources.length, brief: event.lens_briefs.reader, points: event.lens_points?.reader ?? [], available: event.available_lenses ?? [] }
    : null;
  return (
    <section data-theme="dark" className="border-y" style={{ background: "var(--bg)", color: "var(--ink)", borderColor: "var(--line)" }} aria-labelledby="lens-title">
      <div className="sc-shell grid gap-10 py-16 lg:grid-cols-2 lg:items-start">
        <Reveal>
          <p className="p-eyebrow" style={{ color: "var(--accent)" }}>The signature</p>
          <h2 id="lens-title" className="mt-2" style={{ font: "var(--t-display-l)", letterSpacing: "var(--track-display)" }}>The same facts, read for your work.</h2>
          <p className="mt-2.5" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            {story ? "Tap a lens. The record re-sets in place." : "Every story can be read through a lens for your work. The record underneath never changes; only the reading does."}
          </p>
          {story && (
            <p className="mt-4" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
              On today&rsquo;s record: <Link href={`/story/${story.id}`} className="p-link" style={{ color: "var(--accent)" }}>{story.title}</Link>
            </p>
          )}
        </Reveal>
        <div className="min-w-0">{story ? <LensFlip story={story} /> : <LensRegistry />}</div>
      </div>
    </section>
  );
}
