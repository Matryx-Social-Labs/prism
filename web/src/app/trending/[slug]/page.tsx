import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";

import { fetchTrendingStory, type TrendingStoryDetail } from "@/lib/api";
import { StoryArc } from "@/components/reading/StoryArc";
import { jsonLd, storyLd } from "@/lib/seo";

// Rendered once a minute, not per request: nothing server-rendered here varies
// by reader (the lens unlock is client-side), so a crawler hitting thousands of
// records and a reader opening one share the cached shell (audit: force-dynamic
// dated from the scaffold and cost a Railway round trip per view).
export const revalidate = 60;

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

  return (
    <>
      {/* The arc as an article whose parts are its developments (lib/seo). */}
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(storyLd(s)) }} />
      <StoryArc s={s} />
    </>
  );
}
