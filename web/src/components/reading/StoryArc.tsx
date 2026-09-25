import Link from "next/link";

import { Attention } from "@/components/Attention";
import { BranchTree } from "@/components/BranchTree";
import { CoverageBar, CoverageLegend, OutletIcon } from "@/components/Coverage";
import { PhotoDeck } from "@/components/PhotoDeck";
import { PhotoImg } from "@/components/PhotoImg";
import { Rail } from "@/components/Rail";
import { RelatedRoutes } from "@/components/RelatedRoutes";
import { RouteMap } from "@/components/RouteMap";
import { SectionHead } from "@/components/SectionHead";
import { ShareButton } from "@/components/ShareButton";
import { StatusPill } from "@/components/StatusPill";
import { StoryTimeline } from "@/components/StoryTimeline";
import { BackBar } from "@/components/ui";
import type { StoryDevelopment, TrendingStoryDetail } from "@/lib/api";
import { coverageText, publishers } from "@/lib/coverage";
import { shortDate } from "@/lib/dateline";
import { REPORT_IMAGES } from "@/lib/images";
import { framesFromStory } from "@/lib/photos";
import { sectorGroup } from "@/lib/sectors";
import { spanDays, spineLength } from "@/lib/spine";

/**
 * The whole story (Design System v2 · Reading board, flow 02): status, the
 * counted meta, the story's name. A verified story draws its route map ("How
 * it unfolded", across on a desktop and down on a phone) and every
 * development ("All developments"); a provisional grouping lists its related
 * reporting on dashed rules and says no order is implied. Then the latest
 * record. Beside it on a desktop, beneath it on a phone: sources per day
 * (uncounted days hatched), the coverage split with its legend, and Share.
 * Who reported it and who is in it follow — real lists the board does not draw.
 *
 * A server component: the parts that move (the map, the tree, the chart's
 * table toggle, Share) are client components of their own.
 */
const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** The most recent development by its own date; the last listed wins a tie. */
function latestOf(devs: StoryDevelopment[]): StoryDevelopment | null {
  let best: StoryDevelopment | null = null, bestT = -Infinity;
  for (const d of devs) {
    const t = d.occurred_at ? Date.parse(d.occurred_at) : NaN;
    if (!Number.isNaN(t) && t >= bestT) { best = d; bestT = t; }
  }
  return best ?? devs.at(-1) ?? null;
}

function RailHead({ id, children }: { id: string; children: React.ReactNode }) {
  return <h2 id={id} className="p-eyebrow mb-1 pb-2" style={{ borderBottom: "var(--rule-section) solid var(--ink)" }}>{children}</h2>;
}

export function StoryArc({ s }: { s: TrendingStoryDetail }) {
  const verified = s.boundary_status === "verified";
  const tree = verified && s.branches && s.branches.nodes.length > 0 ? s.branches : null;
  const days = spanDays(s.developments);
  const group = sectorGroup(s.sector);
  // Distinct mastheads (The Hindu's state feeds count once), so the bar, its
  // count, the legend and the meta line all print the same number.
  const outlets = publishers((s.outlets ?? []).map((o) => o.outlet));
  const outletN = outlets.length || s.source_count;
  // No development is "here" on the story's own page: that mark belongs to a record.
  const developments = s.developments.map((d) => (d.is_current ? { ...d, is_current: false } : d));
  const nDev = s.developments.length;
  const meta = [days ? plural(days, "day", "days") : null, plural(nDev, "development", "developments"), plural(outletN, "outlet", "outlets")].filter((x): x is string => Boolean(x));
  // A main line of one or two stations has nothing to fold: open the list on everything.
  const openAll = !tree || spineLength(tree) < 3;
  const latest = latestOf(s.developments);
  const dated = s.developments.some((d) => d.occurred_at);
  const photos = s.photos ?? [];
  const url = `/trending/${s.canonical_slug}`;

  const head = (
    <header className="grid gap-2.5">
      <div className="flex flex-wrap items-center gap-2">
        <StatusPill status={verified ? "verified" : "provisional"} label={verified ? "Verified" : "Provisional grouping"} />
        <span className="p-meta">
          {group && <><span className="p-meta__subject">{group.name}</span><span className="p-meta__sep" /></>}
          {meta.map((m, i) => (
            <span key={m} className="contents">{i > 0 && <span className="p-meta__sep" />}<span className="p-meta__prov">{m}</span></span>
          ))}
        </span>
      </div>
      <h1 className="text-balance [font:var(--t-display-m)] lg:[font:var(--t-display-l)]" style={{ letterSpacing: "var(--track-display)" }}>{s.label}</h1>
      <p className="max-w-[60ch]" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
        {verified ? "A story headline written from its developments." : "These reports may belong together. Prism has not confirmed an order of events."}
      </p>
    </header>
  );

  const route = verified ? (
    <>
      {tree && (
        <section aria-labelledby="route-title">
          <SectionHead
            id="route-title"
            title="How it unfolded"
            sub={[plural(tree.shape.developments, "development", "developments"), plural(tree.shape.branches, "branch", "branches"), ...(tree.shape.satellites ? [`${tree.shape.satellites} also reported`] : [])].join(" · ")}
          />
          <div className="mt-2"><RouteMap tree={tree} developments={developments} /></div>
        </section>
      )}
      <section aria-labelledby="list-title">
        <SectionHead id="list-title" title="All developments" sub={tree ? "main line and branches" : plural(nDev, "development", "developments")} />
        <div className="mt-2">
          {tree ? (
            <BranchTree tree={tree} developments={developments} defaultAll={openAll} readout={false} />
          ) : (
            <StoryTimeline story={{ developments, cast: s.timeline_cast }} />
          )}
        </div>
      </section>
    </>
  ) : (
    <section aria-labelledby="related-reporting-title">
      <h2 id="related-reporting-title" className="sr-only">Related reporting</h2>
      <p className="mb-2" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>Related reporting, grouped automatically and under review. No chronology implied.</p>
      <StoryTimeline story={{ developments, cast: [] }} mode="related" />
    </section>
  );

  const latestRow = latest && (
    <section aria-labelledby="latest-title">
      <SectionHead id="latest-title" title="The latest record" />
      <div className="mt-2"><LatestRecord d={latest} s={s} /></div>
    </section>
  );

  const rail = (
    <Rail className="grid min-w-0 content-start gap-6" label="About this story">
      {dated && (
        <section aria-labelledby="attention-title">
          <RailHead id="attention-title">Sources per day</RailHead>
          <Attention developments={developments} />
        </section>
      )}
      <section aria-labelledby="coverage-title" className="grid gap-2">
        <RailHead id="coverage-title">Coverage</RailHead>
        <span className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-1.5">
          <CoverageBar outlets={outlets} fallbackCount={s.source_count} size="lg" width={300} draw className="max-w-full" />
          <span className="p-count" style={{ fontSize: 12.5, color: "var(--ink-2)" }}>{coverageText(outlets, s.source_count)}</span>
        </span>
        {outlets.length > 0 && <CoverageLegend outlets={outlets} />}
      </section>
      <ShareButton url={url} title={s.label} fill />
      {(s.outlets ?? []).length > 0 && (
        <section aria-labelledby="outlets-title">
          <RailHead id="outlets-title">Who reported it · <span className="font-mono">{s.outlets.length}</span></RailHead>
          <ol>
            {s.outlets.slice(0, 12).map(({ outlet, reports }) => (
              <li key={outlet.slug} className="flex items-center gap-2.5 border-b py-2" style={{ borderColor: "var(--line)" }}>
                <OutletIcon domain={outlet.domain} code={outlet.code} name={outlet.name} size={24} />
                <span className="min-w-0 flex-1 truncate" style={{ font: "var(--t-ui)" }}>{outlet.name}</span>
                <span className="p-count">{plural(reports, "report", "reports")}</span>
              </li>
            ))}
          </ol>
          {s.outlets.length > 12 && <p className="p-count mt-2">+{s.outlets.length - 12} more</p>}
        </section>
      )}
      {s.cast.length > 0 && (
        <section aria-labelledby="cast-title">
          <RailHead id="cast-title">Who is in it · <span className="font-mono">{s.cast.length}</span></RailHead>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {(s.cast_refs?.length ? s.cast_refs : s.cast.map((name) => ({ name, slug: null }))).slice(0, 12).map((c) =>
              c.slug ? <Link key={c.name} href={`/entity/${c.slug}`} className="p-chip">{c.name}</Link> : <span key={c.name} className="p-chip">{c.name}</span>,
            )}
          </div>
        </section>
      )}
    </Rail>
  );

  return (
    <>
      {/* display:contents, so the bar sticks to the page and not to a wrapper its own height. */}
      <div className="contents lg:hidden"><BackBar label="Stories" href="/trending" /></div>
      <div className="mx-auto grid max-w-[1020px] gap-8 px-[var(--gutter)] pb-[calc(var(--tabbar)+32px)] pt-4 lg:grid-cols-[minmax(0,640px)_340px] lg:justify-center lg:gap-10 lg:pb-16 lg:pt-8">
        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-6">
          {head}
          {route}
          {latestRow}
          {photos.length > 0 && (
            <section aria-labelledby="photos-title">
              <SectionHead id="photos-title" title="From the reports" sub={plural(photos.length, "photograph", "photographs")} />
              <div className="mt-3"><PhotoDeck frames={framesFromStory(photos)} /></div>
            </section>
          )}
          {(s.related?.length ?? 0) > 0 && (
            <section aria-labelledby="related-title">
              <SectionHead id="related-title" title="Related stories" hint="Different stories that touch this one, by the cast they share or a causal note across the boundary. Not part of this story." />
              <div className="mt-2"><RelatedRoutes related={s.related} /></div>
            </section>
          )}
        </div>
        {rail}
      </div>
    </>
  );
}

/**
 * The latest development as a record row: its subject and date, its title,
 * its sources, and its photograph when the story's photos can credit it.
 */
function LatestRecord({ d, s }: { d: StoryDevelopment; s: TrendingStoryDetail }) {
  const subject = sectorGroup(d.sector)?.name;
  const credit = d.image_url ? (s.photos ?? []).find((p) => p.url === d.image_url)?.outlet ?? null : null;
  const photo = REPORT_IMAGES && d.image_url ? d.image_url : null;
  const prov = [d.occurred_at ? shortDate(d.occurred_at) : null, d.source_count != null ? plural(d.source_count, "source", "sources") : null].filter((x): x is string => Boolean(x));
  return (
    <Link href={`/story/${d.id}`} className="p-row group" style={{ padding: "14px 16px" }}>
      <div className="flex items-start gap-3">
        <div className="grid min-w-0 flex-1 gap-1.5">
          <span className="p-meta">
            {subject && <><span className="p-meta__subject">{subject}</span>{prov.length > 0 && <span className="p-meta__sep" />}</>}
            {prov.map((p, i) => <span key={p} className="contents">{i > 0 && <span className="p-meta__sep" />}<span className="p-meta__prov">{p}</span></span>)}
          </span>
          <h3 className="p-row__title">{d.title}</h3>
        </div>
        {photo && (
          <figure className="p-thumb" style={{ width: 108, height: 80 }}>
            <PhotoImg src={photo} alt={credit ? `Photo: ${credit.name}` : "Photo from a report on this story"} />
            {credit && (
              <figcaption className="p-thumb__credit" title={`Photo: ${credit.name}`}>
                <OutletIcon domain={credit.domain} code={credit.code} name={credit.name} size={16} />
              </figcaption>
            )}
          </figure>
        )}
      </div>
    </Link>
  );
}
