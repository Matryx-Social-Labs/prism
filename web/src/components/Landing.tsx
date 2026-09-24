import Link from "next/link";
import { AskDemo } from "@/components/AskDemo";
import { BranchTree } from "@/components/BranchTree";
import { ChartRow } from "@/components/ChartRow";
import { CoverageBar, CoverageLegend, MonogramStack } from "@/components/Coverage";
import { coverageText, publishers, type Origin } from "@/lib/coverage";
import { HeroLensDemo } from "@/components/HeroLensDemo";
import { LensRegistry } from "@/components/LensRegistry";
import { PrismFigure } from "@/components/PrismFigure";
import { Said } from "@/components/Said";
import { SectionHead } from "@/components/SectionHead";
import { AVAILABLE, FREE_LINE, NEXT, StatusColumn, VALIDATION } from "@/components/StatusGrid";
import { OutletIcon } from "@/components/Coverage";
import { ArrowRight } from "@/components/icons";
import { fallbackCode, indexSources } from "@/lib/sources";
import { monitoredText } from "@/lib/coverage";
import {
  fetchEvent,
  fetchFeed,
  fetchSources,
  fetchTrendingStory,
  type EventDetail,
  type FeedItem,
  type OutletRef,
  type TrendingStoryDetail,
} from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { relativeTime } from "@/lib/dateline";
import { spineLength } from "@/lib/spine";

/**
 * The landing (DESIGN.md § Landing): a product page built from the product's
 * own components on real data. The promise, the prism figure and the live lead
 * row; three proof cards each running a real component (timeline, quote card,
 * coverage bar); the lens flip; an honest Available / In validation / Next
 * grid; one final call. No device mockups, no stock photography, no number
 * that is not counted.
 */
const CTA = "Open today’s record";
const SHELL = "mx-auto w-full max-w-[var(--shell)] px-5 sm:px-8 xl:px-10";

type Evidence = {
  rows: FeedItem[];
  lead: EventDetail | null;
  said: EventDetail | null;
  route: { event: EventDetail; story: TrendingStoryDetail } | null;
  outlets: number;
  languages: number;
  /** Outlets Prism monitors: the denominator every count on the page is out of. */
  monitored: number | null;
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
    // Counted from the window, never typed: distinct mastheads and languages
    // across every row that carries outlet facts.
    const outletRefs = all.flatMap((i) => i.outlets ?? []);
    return {
      rows: rows.slice(0, 5),
      lead: events.find((e) => e.id === rows[0]?.id) ?? events[0] ?? null,
      said: events.find((event) => (event.claims ?? []).length > 0) ?? null,
      route,
      outlets: new Set(outletRefs.map((o) => o.publisher)).size,
      languages: new Set(outletRefs.map((o) => o.language ?? "en")).size,
      monitored: monitored?.outlets ?? null,
    };
  } catch {
    return null;
  }
}

/** Registered-source facts from a record's own report list. */
function outletsOf(event: EventDetail | null): OutletRef[] {
  if (!event) return [];
  return event.sources
    .filter((s) => s.code && s.origin)
    .map((s) => ({ slug: s.source_slug, publisher: s.publisher ?? s.source_slug, name: s.source_name, code: s.code!, origin: s.origin as Origin, language: s.language ?? null, domain: s.domain ?? null }));
}

export async function Landing() {
  const evidence = await loadEvidence();
  const leadRow = evidence?.rows[0] ?? null;
  const lead = evidence?.lead ?? null;
  const said = evidence?.said ?? null;
  const proof = said ?? lead;
  const proofOutlets = outletsOf(proof);
  const reports = proof ? [...proof.sources].sort((a, b) => (b.published_at ?? "").localeCompare(a.published_at ?? "")).slice(0, 3) : [];
  const quote = said?.claims?.[0] ?? null;

  return (
    <div className="pb-24 lg:pb-20">
      {/* ── The promise, the prism, the live record ─────────────── */}
      <section className="relative overflow-hidden border-b" style={{ borderColor: "var(--line)" }}>
        <div className={`${SHELL} relative grid gap-10 py-10 md:py-14 lg:min-h-[calc(100dvh-var(--topbar)-72px)] lg:grid-cols-[minmax(0,.86fr)_minmax(560px,1.14fr)] lg:items-center lg:gap-16 lg:py-16`}>
          <div>
            <p className="mb-4 font-mono text-[11px] font-medium uppercase tracking-[0.08em]" style={{ color: "var(--accent)" }}>The live record · India</p>
            <h1 className="font-record max-w-[12ch] text-[40px] font-bold leading-[1.12] text-balance sm:text-[50px] lg:text-[56px]">
              Follow the story, not the headlines.
            </h1>
            <p className="mt-5 max-w-[44ch] text-[17px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
              Prism assembles each story once from the outlets it monitors and keeps the evidence attached: every report, the exact words said, which outlets covered it and how many have not yet. Then read the same facts through the lens of your work.
            </p>
            <div className="mt-7 flex flex-wrap items-center gap-2.5">
              <Link href="/feed" className="btn btn-primary btn-lg">{CTA} <ArrowRight /></Link>
              <a href="#proof" className="btn btn-ghost btn-lg">How it works</a>
            </div>
            {evidence && evidence.outlets > 0 && (
              <div className="mt-8 grid grid-cols-3 border-y" style={{ borderColor: "var(--line)" }}>
                {[[String(evidence.outlets), evidence.monitored && evidence.monitored >= evidence.outlets ? `of ${evidence.monitored} monitored outlets in today's record` : "outlets in today's record"], [String(evidence.languages), evidence.languages === 1 ? "language read" : "languages read"], ["1", "record per story"]].map(([n, l]) => (
                  <div key={l} className="border-r px-3.5 py-4 last:border-r-0" style={{ borderColor: "var(--line)" }}>
                    <b className="font-record block text-[28px] font-bold leading-none">{n}</b>
                    <span className="mt-1 block text-[12.5px]" style={{ color: "var(--ink-3)" }}>{l}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div>
            <PrismFigure className="mx-auto mb-6 block w-full max-w-[460px]" />
            {leadRow ? (
              <ol className="flex flex-col gap-3" aria-label={`Open live record: ${leadRow.title}`}>
                <ChartRow item={{ ...leadRow, outlets: leadRow.outlets?.length ? leadRow.outlets : outletsOf(lead) }} lead />
              </ol>
            ) : (
              <div className="card" role="status">
                <p className="font-record text-[22px] font-bold leading-[1.25]">The live record is unavailable right now.</p>
                <p className="mt-2 text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>Prism will show current reporting here when the monitored feed reconnects.</p>
                <Link href="/feed" className="btn btn-secondary btn-sm mt-4">Try today&rsquo;s record</Link>
              </div>
            )}
            {leadRow && (
              <p className="mt-2.5 px-1 font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-3)" }}>
                Live · updated {relativeTime(leadRow.latest_published_at ?? leadRow.last_updated_at)}
              </p>
            )}
          </div>
        </div>
      </section>

      {/* ── What you get on every story: three real components ────── */}
      <section id="proof" className={`${SHELL} scroll-mt-20 border-t py-12 lg:py-16`} style={{ borderColor: "var(--line)" }} aria-labelledby="proof-title">
        <p className="mb-2 text-[12.5px] font-semibold uppercase tracking-[0.08em]" style={{ color: "var(--accent)" }}>What you get on every story</p>
        <h2 id="proof-title" className="font-record text-[30px] font-bold leading-[1.15] tracking-[-0.015em] lg:text-[38px]">The record, not a verdict.</h2>
        <p className="mt-2 max-w-[56ch] text-[16.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>Three things a headline can&rsquo;t give you, built from the reports themselves{proof ? `, shown here on a story from today's record` : ""}.</p>
        <div className="mt-7 grid gap-4 lg:grid-cols-3">
          <div className="card flex flex-col gap-3 p-5">
            <h3 className="font-record text-[22px] font-bold leading-[1.2]">What changed</h3>
            <p className="text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>Every report on the story, newest first, with the outlet and the time it published, so a new report never erases what came before it.</p>
            <div className="mt-auto border-t pt-4" style={{ borderColor: "var(--line)" }}>
              {reports.length > 0 ? (
                <ol className="relative">
                  <span aria-hidden className="absolute bottom-2 left-[5px] top-2 w-px" style={{ background: "var(--line-strong)" }} />
                  {reports.map((s, i) => (
                    <li key={s.article_id} className="relative pb-3 pl-6 last:pb-0">
                      <span aria-hidden className="absolute left-0 top-[6px] h-[11px] w-[11px] rounded-full border-2" style={i === 0 ? { background: "var(--accent)", borderColor: "var(--accent)", boxShadow: "0 0 0 4px var(--accent-soft)" } : { background: "var(--surface)", borderColor: "var(--ink)" }} />
                      <p className="flex items-center gap-1.5 text-[12px]" style={{ color: "var(--ink-3)" }}>
                        <OutletIcon domain={s.domain} code={s.code ?? fallbackCode(s.source_name)} name={s.source_name} size={18} />
                        <span className="font-semibold" style={{ color: "var(--ink-2)" }}>{s.source_name}</span>
                        {s.published_at && <span className="font-mono text-[11px]">{relativeTime(s.published_at)}</span>}
                      </p>
                      <p className="font-record mt-0.5 text-[15px] font-bold leading-[1.35] [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:2] overflow-hidden">{s.title}</p>
                    </li>
                  ))}
                </ol>
              ) : (
                <p className="font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-3)" }}>Live example unavailable</p>
              )}
            </div>
          </div>

          <div className="card flex flex-col gap-3 p-5" aria-labelledby="evidence-title">
            <h3 id="evidence-title" className="font-record text-[22px] font-bold leading-[1.2]">Exact words. Exact source.</h3>
            <p className="text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>A quote appears only when the same words are in the article, attributed to the speaker and linked to the line they came from. No paraphrase, no invented positions.</p>
            <div className="mt-auto border-t pt-4 [&_.card]:border-0 [&_.card]:p-0" style={{ borderColor: "var(--line)" }}>
              {said && quote ? (
                <>
                  <Said claims={[{ ...quote, claims: quote.claims.slice(0, 1) }]} sourceIndex={indexSources(said.sources)} />
                  <Link href={`/story/${said.id}#said`} className="mt-3 inline-block text-[13.5px] font-semibold hover:underline underline-offset-4" style={{ color: "var(--accent)" }}>Every verified quote on this story →</Link>
                </>
              ) : (
                <p className="text-[14px]" style={{ color: "var(--ink-3)" }}>No story in the current window carries a verified quote yet.</p>
              )}
            </div>
          </div>

          <div className="card flex flex-col gap-3 p-5">
            <h3 className="font-record text-[22px] font-bold leading-[1.2]">Who covered it, and how sure</h3>
            <p className="text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>See whether a story is carried by English national outlets, Indian-language outlets or the international press. Every count is out of the outlets Prism monitors, and a story only one of them has is marked not yet corroborated.</p>
            <div className="mt-auto border-t pt-4" style={{ borderColor: "var(--line)" }}>
              {proofOutlets.length > 0 ? (
                <>
                  <p className="flex items-center gap-3">
                    <CoverageBar outlets={proofOutlets} size="lg" width={180} />
                    <span className="font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>{coverageText(proofOutlets)}</span>
                  </p>
                  <p className="mt-2 font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>
                    <Link href="/sources" className="underline-offset-4 hover:underline">{monitoredText(publishers(proofOutlets).length, proof?.monitored_outlets ?? evidence?.monitored)}</Link>
                    {proof?.monitored_checked_at && ` · checked ${relativeTime(proof.monitored_checked_at)}`}
                  </p>
                  <div className="mt-3"><CoverageLegend outlets={proofOutlets} /></div>
                  <div className="mt-3"><MonogramStack outlets={proofOutlets} limit={6} /></div>
                  <p className="mt-2 text-[12.5px]" style={{ color: "var(--ink-3)" }}>{publishers(proofOutlets).map((o) => o.name).slice(0, 6).join(" · ")}</p>
                </>
              ) : (
                <p className="font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-3)" }}>Live example unavailable</p>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* ── Live now: the rest of the record's top rows ───────────── */}
      <section id="live-proof" className={`${SHELL} scroll-mt-20 border-t py-12`} style={{ borderColor: "var(--line)" }} aria-labelledby="chart-title">
        <SectionHead id="chart-title" title="Live now" hint={evidence ? "The most-corroborated stories in today's record, as every reader sees them." : "The live record is unreachable right now."} right={<Link href="/feed" className="btn btn-secondary btn-sm">Open today&rsquo;s record</Link>} />
        {evidence && evidence.rows.length > 1 ? (
          <ol className="chart-print grid gap-3 lg:grid-cols-2">
            {evidence.rows.slice(1).map((item) => <ChartRow key={item.id} item={item} />)}
          </ol>
        ) : (
          <div className="card py-6"><p className="text-[15px]" style={{ color: evidence ? "var(--ink-2)" : "var(--danger)" }}>{evidence ? "Nothing is on today’s record yet." : "The live record cannot be reached right now."}</p></div>
        )}
      </section>

      {/* ── See what changed: only with a verified route ─────────── */}
      {evidence?.route && (
        <section className={`${SHELL} border-t py-12`} style={{ borderColor: "var(--line)" }} aria-labelledby="developments-title">
          <SectionHead id="developments-title" title="See what changed" hint="Verified developments stay in order, so a new report does not erase what happened before it." />
          <div className="grid gap-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(480px,1.2fr)] lg:gap-14">
            <Link href={`/story/${evidence.route.event.id}`} className="font-record block text-[22px] font-bold leading-[1.3] text-balance underline-offset-4 hover:underline">
              {evidence.route.event.title}
            </Link>
            <div className="min-w-0">
              <BranchTree tree={evidence.route.story.branches!} developments={evidence.route.story.developments} currentId={evidence.route.event.id} />
            </div>
          </div>
        </section>
      )}

      {/* ── The signature: the same facts, read for your work ─────── */}
      <section className={`${SHELL} border-t py-12 lg:py-16`} style={{ borderColor: "var(--line)" }} aria-labelledby="lens-title">
        <div className="grid gap-8 lg:grid-cols-[minmax(0,0.8fr)_minmax(0,1.2fr)] lg:items-start lg:gap-14">
          <div>
            <p className="mb-2 text-[12.5px] font-semibold uppercase tracking-[0.08em]" style={{ color: "var(--accent)" }}>The signature</p>
            <h2 id="lens-title" className="font-record text-[30px] font-bold leading-[1.15] tracking-[-0.015em] lg:text-[38px]">The same facts, read for your work.</h2>
            <p className="mt-2 max-w-[44ch] text-[16.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>Flip a story into the reading your work needs. The record underneath never changes; only the reading does, and every lens shows what it adds before you sign in.</p>
            <div className="mt-6"><LensRegistry /></div>
          </div>
          <div className="flex flex-col gap-6">
            <HeroLensDemo />
            <div>
              <p className="mb-2 font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>Illustration</p>
              <AskDemo />
            </div>
          </div>
        </div>
      </section>

      {/* ── Honest about what's live ──────────────────────────────── */}
      <section id="status" className={`${SHELL} scroll-mt-20 border-t py-12 lg:py-16`} style={{ borderColor: "var(--line)" }} aria-labelledby="status-title">
        <p className="mb-2 text-[12.5px] font-semibold uppercase tracking-[0.08em]" style={{ color: "var(--accent)" }}>Where Prism stands today</p>
        <h2 id="status-title" className="font-record text-[30px] font-bold leading-[1.15] tracking-[-0.015em] lg:text-[38px]">Honest about what&rsquo;s live.</h2>
        <div className="mt-7 grid gap-3 md:grid-cols-3">
          <StatusColumn tone="now" label="Available now" items={AVAILABLE} />
          <StatusColumn tone="val" label="In validation" items={VALIDATION} />
          <StatusColumn tone="next" label="Next" items={NEXT} />
        </div>
        <p className="mt-6 max-w-[64ch] text-[14.5px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>
          {FREE_LINE}
        </p>
      </section>

      {/* ── One final call ────────────────────────────────────────── */}
      <section className={`${SHELL} border-t py-14 text-center`} style={{ borderColor: "var(--line)" }}>
        <h2 className="font-record text-[32px] font-bold leading-[1.1] tracking-[-0.015em]">Open today&rsquo;s record.</h2>
        <div className="mt-5 flex flex-wrap items-center justify-center gap-2.5">
          <Link href="/feed" className="btn btn-primary btn-lg">Read today <ArrowRight /></Link>
          <Link href="/onboarding" className="btn btn-ghost btn-lg">Set up my feed</Link>
        </div>
        <p className="mt-3 text-[14px]" style={{ color: "var(--ink-3)" }}>Free. No account needed to read.</p>
      </section>
    </div>
  );
}
