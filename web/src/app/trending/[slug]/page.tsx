import type { Metadata } from "next";
import { notFound, redirect } from "next/navigation";
import Link from "next/link";

import { fetchTrendingStory, type TrendingStoryDetail } from "@/lib/api";
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

  return (
    <div className="mx-auto max-w-[820px] px-5 pb-24 pt-8 sm:px-8">
      <Link href="/trending" className="mb-5 block text-[12.5px] font-semibold" style={{ color: "var(--ink-faint)" }}>
        ← Trending
      </Link>

      <p
        className="text-[11px] font-semibold uppercase tracking-[0.14em]"
        style={{ color: "var(--ink-faint)", fontFamily: "var(--font-mono), monospace" }}
      >
        Trending · {s.source_count} outlets · {s.velocity > 0 ? "developing now" : "developing"}
      </p>
      <h1 className="mt-2 text-[30px] font-semibold leading-tight sm:text-[36px]" style={{ fontFamily: "var(--font-display), serif" }}>
        {s.label}
      </h1>

      <div className="mt-4 flex flex-wrap items-center gap-2">
        <ShareButton url={`/trending/${s.canonical_slug}`} title={s.label} />
        {s.cast.slice(0, 4).map((c) => (
          <span
            key={c}
            className="rounded-full border px-3 py-1 text-[12.5px]"
            style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}
          >
            {c}
          </span>
        ))}
      </div>

      <div className="mt-8">
        <StoryTimeline story={{ developments: s.developments, cast: s.timeline_cast }} />
      </div>
    </div>
  );
}
