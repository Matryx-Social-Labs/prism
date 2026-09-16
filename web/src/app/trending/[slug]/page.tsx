import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import Link from "next/link";

import { fetchTrendingStory, type TrendingStoryDetail } from "@/lib/api";
import { Attention } from "@/components/Attention";
import { BranchTree } from "@/components/BranchTree";
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
export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const s = await load(slug);
  if (!s) return { title: "Story not found" };
  const description = blurb(s);
  return {
    title: `${s.label} — Prism`,
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

  const tree = s.branches && s.branches.nodes.length > 0 ? s.branches : null;
  const shape = tree ? `${tree.shape.developments} developments · ${tree.shape.branches} branches · ${tree.shape.satellites} satellites` : `${s.developments.length} developments`;

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 pt-4 sm:px-8 lg:pb-16">
      {/* The strip: what is true of the whole story */}
      <div className="rule-live flex flex-wrap gap-x-3 pt-3 font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-faint)" }}>
        <span>{s.sector ?? "story"}</span><span>· {shape}</span><span>· {s.source_count} outlets</span>{s.velocity > 0 && <span style={{ color: "var(--ink)" }}>· moving</span>}
      </div>
      <h1 className="mt-2 text-[26px] font-medium leading-[1.2] text-balance sm:text-[32px] lg:max-w-[30ch]">{s.label}</h1>
      <p className="mt-2 font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-faint)" }}>
        Story headline · from {s.developments.length} developments
      </p>

      {/* The route: the whole story as the rail map, then the attention curve on request */}
      {tree ? (
        <section className="mt-6" aria-labelledby="route-title">
          <SectionHead id="route-title" title="The route" hint="Every development on its line: the main line, its branches, the branch lines that grew their own stations, and what was reported off the main line. Tap a station." />
          <RouteMap tree={tree} developments={s.developments} />
          <Attention tree={tree} developments={s.developments} />
        </section>
      ) : null}

      <div className="mt-8 grid gap-10 lg:grid-cols-[minmax(0,720px)_1fr] lg:gap-16">
        <div>
          <SectionHead id="list-title" title="Every station, as a list" count={s.developments.length} />
          {tree ? (
            <BranchTree tree={tree} developments={s.developments} />
          ) : (
            <StoryTimeline story={{ developments: s.developments, cast: s.timeline_cast }} />
          )}
        </div>
        <aside>
          <SectionHead id="cast-title" title="Who is in it" count={s.cast.length} />
          <ul>
            {s.cast.slice(0, 8).map((c) => (
              <li key={c} className="rule-live py-2 text-[14.5px]">{c}</li>
            ))}
          </ul>
          <div className="rule-live mt-6 pt-4">
            <ShareButton url={`/trending/${s.canonical_slug}`} title={s.label} />
          </div>
          <Link href="/trending" className="mt-6 block font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline" style={{ color: "var(--ink-muted)" }}>
            ← All trending
          </Link>
        </aside>
      </div>
    </div>
  );
}
