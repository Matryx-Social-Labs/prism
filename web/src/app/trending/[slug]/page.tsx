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
  return `${s.source_count} outlets · ${s.developments.length} developments — ${base}`.slice(0, 200);
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

const MONO = "font-mono text-[11px] uppercase tracking-[0.04em]";

export default async function TrendingStoryPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const s = await load(slug);
  if (!s) notFound();
  // Merged story → the request slug resolved to a canonical one; move the URL there.
  if (s.canonical_slug !== slug) redirect(`/trending/${s.canonical_slug}`);

  const tree = s.branches && s.branches.nodes.length > 0 ? s.branches : null;
  const days = spanDays(s.developments);
  // One shape line, at the top, counted: developments · branches · satellites · days.
  const shape = tree
    ? [`${tree.shape.developments} developments`, `${tree.shape.branches} ${tree.shape.branches === 1 ? "branch" : "branches"}`, `${tree.shape.satellites} ${tree.shape.satellites === 1 ? "satellite" : "satellites"}`, ...(days != null ? [`${days} ${days === 1 ? "day" : "days"}`] : [])]
    : [`${s.developments.length} developments`];
  // A main line of one or two stations has nothing to fold: open the list on everything.
  const openAll = !tree || spineLength(tree) < 3;

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 pt-4 sm:px-8 lg:pb-16">
      <Link href="/trending" className={`${MONO} mb-3 block lg:hidden`} style={{ color: "var(--ink-muted)" }}>
        ← All trending
      </Link>

      {/* The strip: what is true of the whole story, and Share on the same rule */}
      <div className="rule-live flex items-start justify-between gap-4 pt-3">
        <div className={`flex flex-wrap gap-x-3 gap-y-1 ${MONO}`} style={{ color: "var(--ink-faint)" }}>
          <span style={{ color: "var(--ink)" }}>{s.sector ?? "story"}</span>
          <span>· {s.source_count} outlets</span>
          {shape.map((x) => <span key={x}>· {x}</span>)}
          {s.velocity > 0 && <span style={{ color: "var(--ink)" }}>· moving</span>}
        </div>
        <span className="flex-none">
          <ShareButton url={`/trending/${s.canonical_slug}`} title={s.label} />
        </span>
      </div>
      <h1 className="mt-2 text-[26px] font-medium leading-[1.2] text-balance sm:text-[32px] lg:max-w-[30ch]">{s.label}</h1>
      <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
        Story headline · from {s.developments.length} developments
      </p>

      <div className="mt-6 grid gap-10 lg:grid-cols-[minmax(0,860px)_1fr] lg:gap-16">
        <div className="min-w-0">
          {/* The route: the whole story as the rail map, the attention curve on request */}
          {tree ? (
            <section aria-labelledby="route-title">
              <SectionHead id="route-title" title="The route" hint="Every development on its line. Tap a station to read it." />
              <RouteMap tree={tree} developments={s.developments} />
              <Attention tree={tree} developments={s.developments} />
            </section>
          ) : null}

          {/* Every station, as a list: the table view of the map */}
          <section className={tree ? "mt-8" : ""} aria-labelledby="list-title">
            <SectionHead id="list-title" title="Every station, as a list" count={s.developments.length} />
            {tree ? (
              <BranchTree tree={tree} developments={s.developments} defaultAll={openAll} readout={false} />
            ) : (
              <StoryTimeline story={{ developments: s.developments, cast: s.timeline_cast }} />
            )}
          </section>
        </div>

        <aside className="lg:sticky lg:top-20 lg:self-start">
          <SectionHead id="cast-title" title="Who is in it" count={s.cast.length} />
          <ul>
            {s.cast.slice(0, 8).map((c) => (
              <li key={c} className="rule-live py-2 text-[14.5px]">{c}</li>
            ))}
          </ul>
        </aside>
      </div>

      {/* Related routes: different stories, so they come after everything that is this one */}
      {(s.related?.length ?? 0) > 0 && (
        <section className="mt-10 lg:max-w-[860px]" aria-labelledby="related-title">
          <SectionHead id="related-title" title="Related routes" hint="Different stories that touch this one, by the cast they share or a causal note across the boundary. Not part of this story." />
          <RelatedRoutes related={s.related} />
        </section>
      )}

      <p className={`rule-live mt-10 flex justify-between gap-4 py-3 ${MONO}`}>
        <Link href="/trending" className="underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>← All trending</Link>
        <Link href="/feed" className="underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>Today&rsquo;s chart →</Link>
      </p>
    </div>
  );
}
