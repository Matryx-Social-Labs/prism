import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import Link from "next/link";

import { fetchTrendingStory, type TrendingStoryDetail } from "@/lib/api";
import { spanDays, spineLength } from "@/lib/spine";
import { Attention } from "@/components/Attention";
import { BranchTree } from "@/components/BranchTree";
import { RelatedRoutes } from "@/components/RelatedRoutes";
import { RouteMap } from "@/components/RouteMap";
import { SectionHead } from "@/components/SectionHead";
import { StoryTimeline } from "@/components/StoryTimeline";
import { ShareButton } from "@/components/ShareButton";
import { StatusPill } from "@/components/StatusPill";
import { CoverageBar, OutletIcon } from "@/components/Coverage";
import { PhotoDeck } from "@/components/PhotoDeck";
import { Rail } from "@/components/Rail";
import { framesFromStory } from "@/lib/photos";
import { ArrowLeft } from "@/components/icons";
import { Brand } from "@/components/Brand";
import { sectorGroup } from "@/lib/sectors";
import { jsonLd, storyLd } from "@/lib/seo";

export const dynamic = "force-dynamic";

async function load(slug: string): Promise<TrendingStoryDetail | null> {
  try {
    return await fetchTrendingStory(slug);
  } catch {
    return null;
  }
}

function blurb(s: TrendingStoryDetail): string {
  const lead = s.developments.find((d) => !d.is_current) ?? s.developments[0];
  const base = lead?.title ?? s.label;
  const members = s.boundary_status === "verified" ? "developments" : "related events";
  return `${s.source_count} outlets · ${s.developments.length} ${members} — ${base}`.slice(0, 200);
}

// The OG image comes from opengraph-image.tsx in this route (branded card) — we
// deliberately do NOT set openGraph.images here so that file convention wins.
// The root template appends "| Prism", so the title is the label alone.
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const s = await load(slug);
  if (!s) return { title: "Story not found" };
  const description = blurb(s);
  return {
    title: s.label,
    description,
    alternates: { canonical: `/trending/${s.canonical_slug}` },
    openGraph: { type: "article", title: s.label, description, url: `/trending/${s.canonical_slug}` },
    twitter: { card: "summary_large_image", title: s.label, description },
  };
}

export default async function TrendingStoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const s = await load(slug);
  if (!s) notFound();
  // Merged story → the request slug resolved to a canonical one; move the URL there.
  if (s.canonical_slug !== slug) redirect(`/trending/${s.canonical_slug}`);

  const verified = s.boundary_status === "verified";
  const tree = verified && s.branches && s.branches.nodes.length > 0 ? s.branches : null;
  const days = spanDays(s.developments);
  // One shape line, at the top, counted: developments · branches · satellites · days.
  const shape = tree
    ? [`${tree.shape.developments} developments`, `${tree.shape.branches} branched off`, `${tree.shape.satellites} also reported`, ...(days != null ? [`${days} ${days === 1 ? "day" : "days"}`] : [])]
    : [`${s.developments.length} ${verified ? "developments" : "related events"}`];
  // A main line of one or two stations has nothing to fold: open the list on everything.
  const openAll = !tree || spineLength(tree) < 3;

  const group = sectorGroup(s.sector);
  return (
    <>
      {/* The arc as an article whose parts are its developments (lib/seo). */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(storyLd(s)) }} />
      <div className="glass sticky top-0 z-30 flex h-[52px] items-center justify-between border-b px-3 sm:px-6 lg:hidden" style={{ borderColor: "var(--line)" }}>
        <Link href="/trending" className="btn btn-ghost btn-sm gap-1.5" aria-label="Back to stories"><ArrowLeft /> Stories</Link>
        <Brand size={22} label="Prism, stories" />
        <span className="w-[86px]" aria-hidden />
      </div>
      <div className="mx-auto max-w-[var(--shell)] px-5 pb-24 pt-4 sm:px-8 lg:pb-16 lg:pt-6 xl:px-10">
        <header className="border-b pb-5" style={{ borderColor: "var(--line)" }}>
          <div className="meta-line flex-wrap">
            <StatusPill status={verified ? "verified" : "provisional"} label={verified ? "Verified story" : "Grouping under review"} />
            {group && <span>{group.name}</span>}
            {s.velocity > 0 && <span style={{ color: "var(--accent)", fontWeight: 600 }}>moving now</span>}
            {days != null && days > 0 && <span>{days} {days === 1 ? "day" : "days"}</span>}
          </div>
          <h1 className="font-record mt-3 max-w-[28ch] text-[30px] font-bold leading-[1.12] text-balance sm:text-[38px]" style={{ letterSpacing: "-0.015em" }}>{s.label}</h1>
          <p className="mt-2 text-[15px]" style={{ color: "var(--ink-2)" }}>
            {verified ? "A story headline written from its developments." : "Related reporting, grouped by subject and cast while the story boundary is under human review. No chronology is implied."}
          </p>
          <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2">
            <span className="inline-flex items-center gap-2.5">
              {/* The bar in the outlets' real slot colours, since the story knows who reported it. */}
              <CoverageBar outlets={(s.outlets ?? []).map((o) => o.outlet)} fallbackCount={s.source_count} size="lg" />
              <span className="font-mono text-[12px]" style={{ color: "var(--ink-3)" }}>{s.source_count} outlets · {shape.join(" · ")}</span>
            </span>
          </div>
          {/* The story's photographs: every development's, credited, one stage. */}
          {(s.photos ?? []).length > 0 && (
            <div className="mt-6 lg:max-w-[var(--reading)]"><PhotoDeck frames={framesFromStory(s.photos)} /></div>
          )}
          <div className="mt-4 hidden lg:flex"><ShareButton url={`/trending/${s.canonical_slug}`} title={s.label} /></div>
        </header>

        <div className="mt-6 grid gap-10 lg:grid-cols-[minmax(0,1fr)_var(--evidence)] lg:gap-12">
          <div className="min-w-0">
            {verified && tree ? (
              <section aria-labelledby="route-title" className="card p-5">
                <SectionHead id="route-title" title="How this story unfolded" hint="Every development in order. Tap one to read it." />
                <RouteMap tree={tree} developments={s.developments} />
                <Attention tree={tree} developments={s.developments} />
              </section>
            ) : null}

            {verified ? (
              <section className={tree ? "mt-8" : ""} aria-labelledby="list-title">
                <SectionHead id="list-title" title="All developments" count={s.developments.length} hint={tree ? undefined : "Oldest to latest, with how each followed from the last."} />
                {tree ? (
                  <BranchTree tree={tree} developments={s.developments} defaultAll={openAll} readout={false} />
                ) : (
                  <StoryTimeline story={{ developments: s.developments, cast: s.timeline_cast }} />
                )}
              </section>
            ) : (
              <section aria-labelledby="related-reporting-title">
                <SectionHead id="related-reporting-title" title="Related reporting" count={s.developments.length} />
                <StoryTimeline story={{ developments: s.developments, cast: [] }} mode="related" />
              </section>
            )}
          </div>

          <Rail className="flex flex-col gap-4">
            {(s.outlets ?? []).length > 0 && (
              <div className="card">
                <h2 id="outlets-title" className="card-h">Who reported it · {s.outlets.length}</h2>
                <ol className="flex flex-col">
                  {s.outlets.slice(0, 12).map(({ outlet, reports }, i) => (
                    <li key={outlet.slug} className={`flex items-center gap-2.5 py-2 ${i > 0 ? "border-t" : ""}`} style={{ borderColor: "var(--line)" }}>
                      <OutletIcon domain={outlet.domain} code={outlet.code} name={outlet.name} size={24} />
                      <span className="min-w-0 flex-1 truncate text-[14px]">{outlet.name}</span>
                      <span className="font-mono text-[11px] tabular-nums" style={{ color: "var(--ink-3)" }}>{reports} {reports === 1 ? "report" : "reports"}</span>
                    </li>
                  ))}
                </ol>
                {s.outlets.length > 12 && <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>+{s.outlets.length - 12} more</p>}
              </div>
            )}
            <div className="card">
              <h2 id="cast-title" className="card-h">Who is in it · {s.cast.length}</h2>
              <div className="flex flex-wrap gap-1.5">
                {s.cast.slice(0, 12).map((c) => (
                  <Link key={c} href={`/search?q=${encodeURIComponent(c)}`} className="chip h-[30px] px-2.5 text-[13px]">{c}</Link>
                ))}
              </div>
            </div>
          </Rail>
        </div>

        {(s.related?.length ?? 0) > 0 && (
          <section className="mt-10 lg:max-w-[860px]" aria-labelledby="related-title">
            <SectionHead id="related-title" title="Related stories" hint="Different stories that touch this one, by the cast they share or a causal note across the boundary. Not part of this story." />
            <RelatedRoutes related={s.related} />
          </section>
        )}

        <p className="mt-10 flex justify-between gap-4 border-t pt-4 text-[13.5px] font-medium" style={{ borderColor: "var(--line)" }}>
          <Link href="/trending" className="underline-offset-4 hover:underline" style={{ color: "var(--ink-2)" }}>← All stories</Link>
          <Link href="/feed" className="underline-offset-4 hover:underline" style={{ color: "var(--accent)" }}>Today&rsquo;s record →</Link>
        </p>
      </div>
      <div className="glass fixed inset-x-0 bottom-0 z-40 flex gap-2 border-t px-4 pt-2.5 lg:hidden" style={{ borderColor: "var(--line)", paddingBottom: "calc(env(safe-area-inset-bottom) + 10px)" }}>
        <div className="flex-1"><ShareButton url={`/trending/${s.canonical_slug}`} title={s.label} fill /></div>
      </div>
    </>
  );
}
