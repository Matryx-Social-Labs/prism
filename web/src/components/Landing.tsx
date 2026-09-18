import Link from "next/link";
import { AskDemo } from "@/components/AskDemo";
import { BranchTree } from "@/components/BranchTree";
import { ChartRow } from "@/components/ChartRow";
import { HeroLensDemo } from "@/components/HeroLensDemo";
import { LensRegistry } from "@/components/LensRegistry";
import { Said } from "@/components/Said";
import { SectionHead } from "@/components/SectionHead";
import { indexSources } from "@/components/SourceList";
import {
  fetchEvent,
  fetchFeed,
  fetchTrendingStory,
  type EventDetail,
  type FeedItem,
  type TrendingStoryDetail,
} from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { istDate, istTime } from "@/lib/dateline";
import { sectorCode } from "@/lib/sectors";
import { spineLength } from "@/lib/spine";

/** The landing is a working front page, not a feature catalogue. */
const CTA = "Open today’s chart";
const SHELL = "mx-auto w-full max-w-[1400px] px-5 sm:px-8 xl:px-10";

type Evidence = {
  rows: FeedItem[];
  sources: number;
  said: EventDetail | null;
  route: { event: EventDetail; story: TrendingStoryDetail } | null;
};

async function loadEvidence(): Promise<Evidence | null> {
  try {
    const all = await fetchFeed({ limit: 60 });
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

    return {
      rows: rows.slice(0, 5),
      sources: rows.reduce((total, item) => total + (item.source_count || 0), 0),
      said: events.find((event) => (event.claims ?? []).length > 0) ?? null,
      route,
    };
  } catch {
    return null;
  }
}

function Action({ children }: { children: React.ReactNode }) {
  return (
    <Link
      href="/feed"
      className="inline-flex h-12 items-center whitespace-nowrap rounded-full px-6 text-[14.5px] font-semibold transition-opacity hover:opacity-85 active:opacity-70"
      style={{ background: "var(--ink)", color: "var(--bg)" }}
    >
      {children}
    </Link>
  );
}

function LiveRecord({ item }: { item: FeedItem | null }) {
  if (!item) {
    return (
      <div className="border" style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)" }} role="status">
        <div className="border-b px-4 py-3 font-mono text-[11px] uppercase tracking-[0.06em]" style={{ borderColor: "var(--line)", color: "var(--ink)" }}>
          Live story record
        </div>
        <div className="grid min-h-[300px] content-end px-5 py-6 sm:min-h-[360px] sm:p-7">
          <p className="max-w-[28ch] text-[22px] font-medium leading-[1.25] text-balance">
            The live record is unavailable right now.
          </p>
          <p className="mt-3 max-w-[42ch] text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>
            Prism will show current reporting here when the monitored feed reconnects.
          </p>
          <Link href="/feed" className="mt-5 w-fit font-mono text-[11px] uppercase tracking-[0.06em] underline underline-offset-4">
            Try today&rsquo;s chart
          </Link>
        </div>
      </div>
    );
  }

  const latestReport = item.latest_published_at ?? item.last_updated_at;
  return (
    <Link
      href={`/story/${item.id}`}
      className="group block border"
      style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)" }}
      aria-label={`Open live record: ${item.title}`}
    >
      <div className="flex items-center justify-between gap-4 border-b px-4 py-3 font-mono text-[11px] uppercase tracking-[0.06em]" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
        <span style={{ color: "var(--ink)" }}>Live story record</span>
        <span>{latestReport ? `Latest report ${istTime(latestReport)}` : "Current record"}</span>
      </div>
      {item.image_url && (
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={item.image_url}
          alt=""
          className="aspect-[16/9] w-full object-cover"
          style={{ filter: "grayscale(0.12) contrast(1.02)" }}
        />
      )}
      <div className="grid grid-cols-[52px_1fr] gap-4 px-4 py-5 sm:grid-cols-[64px_1fr] sm:p-6">
        <span className="font-display text-[46px] leading-[0.85] tabular-nums sm:text-[56px]" aria-label={`${item.source_count} sources`}>
          {item.source_count}
        </span>
        <span className="min-w-0">
          <span className="block text-[20px] font-medium leading-[1.2] text-balance group-hover:underline group-focus-visible:underline underline-offset-4 sm:text-[24px]">
            {item.title}
          </span>
          {item.summary && (
            <span className="mt-2 block text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>
              {item.summary}
            </span>
          )}
          <span className="mt-3 flex flex-wrap gap-x-3 font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-faint)" }}>
            <span>{item.source_count === 1 ? "source" : "sources"}</span>
            {sectorCode(item.sector) && <span>{sectorCode(item.sector)}</span>}
            <span>Open evidence</span>
          </span>
        </span>
      </div>
    </Link>
  );
}

function StatusRow({ label, title, items }: { label: string; title: string; items: string[] }) {
  return (
    <div className="rule-live grid gap-3 py-6 md:grid-cols-[180px_240px_minmax(0,1fr)] md:gap-8">
      <p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }}>{label}</p>
      <h3 className="text-[17px] font-semibold leading-[1.35]">{title}</h3>
      <ul className="grid gap-x-8 gap-y-2 text-[14.5px] leading-[1.5] sm:grid-cols-2" style={{ color: "var(--ink-muted)" }}>
        {items.map((item) => (
          <li key={item} className="flex gap-3">
            <span aria-hidden className="mt-[10px] h-px w-3 shrink-0" style={{ background: "var(--ink)" }} />
            <span>{item}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

const AVAILABLE = [
  "One event record built from monitored outlets",
  "Exact source links and verified quotes",
  "Professional rereads on supported stories",
  "Developments shown when the story boundary is verified",
];

const VALIDATION = [
  "Story-boundary quality with two independent labellers",
  "Freshness measured over a clean 72-hour window",
  "Coverage gaps stated against a defined monitored set",
  "Backlog and historical duplicate cleanup",
];

const NEXT = [
  "Follow a story and see only material changes",
  "Original-language text beside translation",
  "Visible correction and version history",
  "Coverage differences by language, origin and ownership",
];

export async function Landing() {
  const evidence = await loadEvidence();
  const lead = evidence?.rows[0] ?? null;
  const said = evidence?.said ?? null;
  const dateline = evidence
    ? `${istDate(new Date())}. ${evidence.sources.toLocaleString("en-IN")} source reports in the current window.`
    : "The live chart is unreachable right now.";

  return (
    <div className="pb-24 lg:pb-20">
      <section className={`${SHELL} grid gap-9 py-10 md:py-14 lg:min-h-[calc(100dvh-57px)] lg:grid-cols-[minmax(0,0.78fr)_minmax(520px,1.22fr)] lg:content-center lg:gap-14 lg:py-16`}>
        <div className="self-center">
          <h1 className="max-w-[10ch] text-[42px] font-semibold leading-[0.98] tracking-[-0.025em] text-balance sm:text-[54px] lg:text-[64px]">
            Follow the story, not the headlines.
          </h1>
          <p className="mt-5 max-w-[42ch] text-[16px] leading-[1.55] sm:text-[17px]" style={{ color: "var(--ink-muted)" }}>
            One live record from monitored outlets, with every development, quote and source open to inspection.
          </p>
          <div className="mt-7 flex flex-wrap items-center gap-x-6 gap-y-3">
            <Action>{CTA}</Action>
            <a href="#live-proof" className="text-[14.5px] font-medium underline underline-offset-4">See the live proof</a>
          </div>
        </div>
        <LiveRecord item={lead} />
      </section>

      <section className={`${SHELL} border-y py-5`} style={{ borderColor: "var(--line)" }} aria-label="What Prism is">
        <div className="grid gap-5 sm:grid-cols-3 sm:gap-8">
          {[
            ["One record", "Matching reports are combined before you read."],
            ["Open evidence", "Quotes and summaries lead back to the reporting."],
            ["Built for India", "Regional context and Indian-language reading belong in the core product."],
          ].map(([title, body]) => (
            <div key={title}>
              <p className="font-display text-[22px] uppercase leading-none tracking-[0.03em]">{title}</p>
              <p className="mt-2 max-w-[34ch] text-[14px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>{body}</p>
            </div>
          ))}
        </div>
      </section>

      <section id="live-proof" className={`${SHELL} mt-16 scroll-mt-20`} aria-labelledby="chart-title">
        <SectionHead id="chart-title" title="Live now" hint={dateline} />
        {evidence && evidence.rows.length > 0 ? (
          <>
            <ol className="chart-print lg:grid lg:grid-cols-2 lg:gap-x-10">
              {evidence.rows.slice(1).map((item) => <ChartRow key={item.id} item={item} />)}
            </ol>
            <Link href="/feed" className="rule-live block py-4 font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
              Open the full chart
            </Link>
          </>
        ) : (
          <p className="rule-live py-6 text-[15px]" style={{ color: evidence ? "var(--ink-muted)" : "var(--danger)" }}>
            {evidence ? "Nothing is on today’s chart yet." : "The live record cannot be reached right now."}
          </p>
        )}
      </section>

      {evidence?.route && (
        <section className={`${SHELL} mt-16`} aria-labelledby="developments-title">
          <SectionHead id="developments-title" title="See what changed" hint="Verified developments stay in order, so a new report does not erase what happened before it." />
          <div className="grid gap-8 py-6 lg:grid-cols-[minmax(0,0.8fr)_minmax(480px,1.2fr)] lg:gap-14">
            <div>
              {evidence.route.event.image_url && (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={evidence.route.event.image_url} alt="" className="aspect-[16/10] w-full object-cover" style={{ filter: "grayscale(0.14) contrast(1.02)" }} loading="lazy" />
              )}
              <Link href={`/story/${evidence.route.event.id}`} className="mt-4 block text-[20px] font-medium leading-[1.3] text-balance underline-offset-4 hover:underline">
                {evidence.route.event.title}
              </Link>
            </div>
            <div className="min-w-0">
              <BranchTree tree={evidence.route.story.branches!} developments={evidence.route.story.developments} currentId={evidence.route.event.id} />
            </div>
          </div>
        </section>
      )}

      <section className={`${SHELL} mt-16`} aria-labelledby="evidence-title">
        <SectionHead id="evidence-title" title="Exact words. Exact source." hint="A quote appears only when the same words are present in the article. Open it in place to check the context." />
        <div className="grid gap-10 py-6 lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-16">
          <div>
            {said ? (
              <>
                <Said claims={(said.claims ?? []).slice(0, 2).map((speaker) => ({ ...speaker, claims: speaker.claims.slice(0, 2) }))} sourceIndex={indexSources(said.sources)} />
                <Link href={`/story/${said.id}#said`} className="mt-4 inline-block font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
                  Open every verified quote
                </Link>
              </>
            ) : (
              <p className="text-[14.5px]" style={{ color: "var(--ink-faint)" }}>No story in the current window carries a verified quote yet.</p>
            )}
          </div>
          <div className="rule-live pt-5">
            <p className="font-display text-[22px] uppercase leading-none tracking-[0.03em]">Evidence before confidence</p>
            <p className="mt-3 text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
              Source count, outlet, publication time and article context stay visible. If a story group is provisional, Prism says so.
            </p>
          </div>
        </div>
      </section>

      <section className={`${SHELL} mt-16`} aria-labelledby="lens-title">
        <SectionHead id="lens-title" title="The record first. Your work second." hint="The underlying evidence stays fixed. A professional lens changes what the reading pulls forward." />
        <div className="grid gap-10 py-6 lg:grid-cols-[minmax(480px,1.15fr)_minmax(0,0.85fr)] lg:gap-14">
          <HeroLensDemo />
          <div>
            <LensRegistry />
            <div className="rule-live mt-7 pt-5">
              <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-faint)" }}>Illustration</p>
              <AskDemo />
            </div>
          </div>
        </div>
      </section>

      <section className={`${SHELL} mt-16`} aria-labelledby="status-title">
        <SectionHead id="status-title" title="What is ready, and what is not" />
        <StatusRow label="Available now" title="The inspectable record" items={AVAILABLE} />
        <StatusRow label="In validation" title="Quality before reach" items={VALIDATION} />
        <StatusRow label="Next" title="Return only when it matters" items={NEXT} />
      </section>

      <section className={`${SHELL} mt-16`} aria-labelledby="access-title">
        <SectionHead id="access-title" title="Free record. Professional depth." />
        <div className="grid gap-x-14 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)]">
          <div className="rule-live py-6">
            <h3 className="text-[18px] font-semibold">For every reader</h3>
            <p className="mt-2 max-w-[42ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>The live record, sources, verified quotes and visible story status belong in the free product.</p>
          </div>
          <div className="rule-live py-6">
            <h3 className="text-[18px] font-semibold">For work that depends on news</h3>
            <p className="mt-2 max-w-[58ch] text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>Professional rereads, high-signal watchlists, material-change alerts, team digests and audit-ready exports can support a paid product.</p>
          </div>
        </div>
      </section>

      <section className={`${SHELL} rule-live mt-16 flex flex-wrap items-center gap-x-6 gap-y-3 pt-8`}>
        <Action>{CTA}</Action>
        <Link href="/onboarding" className="text-[14.5px] font-medium underline underline-offset-4">Set up my feed</Link>
      </section>
    </div>
  );
}
