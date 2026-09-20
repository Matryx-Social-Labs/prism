import { ImageResponse } from "next/og";

import { fetchTrendingStory } from "@/lib/api";
import { OgCard } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { spanDays } from "@/lib/spine";
import { sectorGroup } from "@/lib/sectors";
import { SITE_URL } from "@/lib/site";

// The story's share card: its headline, how many developments and outlets
// over how many days, who is in it, and the coverage bar built from the
// outlets that reported it. Same shape as a record's card, kicker "Story".
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let headline = "Follow the story, not the headlines.";
  let summary: string | null = null;
  let meta: string[] = [];
  let foot = "";
  let coverage: { national: number; intl: number; regional: number; wire: number } | undefined;
  let coverageText = "";
  let degraded = false;
  try {
    const s = await fetchTrendingStory(slug);
    if (!s) throw new Error("no such story");
    headline = s.label;
    const devs = s.developments.length;
    const days = spanDays(s.developments);
    const verified = s.boundary_status === "verified";
    meta = [sectorGroup(s.sector)?.name ?? "", `${devs} ${verified ? (devs === 1 ? "development" : "developments") : devs === 1 ? "report" : "reports"}`, days != null && days > 0 ? `${days} ${days === 1 ? "day" : "days"}` : ""].filter(Boolean);
    summary = s.cast.length ? `Named: ${s.cast.slice(0, 5).join(", ")}.` : null;
    coverage = { national: 0, intl: 0, regional: 0, wire: 0 };
    for (const o of s.outlets ?? []) if (o.outlet.origin in coverage) coverage[o.outlet.origin as keyof typeof coverage] += o.reports;
    coverageText = `${s.source_count} ${s.source_count === 1 ? "outlet" : "outlets"} · ${devs} ${devs === 1 ? "report" : "reports"}`;
    foot = verified ? "A story headline written from its developments" : "Grouping under review";
  } catch {
    degraded = true;
  }
  const host = SITE_URL.replace(/^https?:\/\//, "");
  const fonts = await ogFonts(headline, summary ?? "", ...meta, coverageText, foot, host, "Prism Story");
  return new ImageResponse(
    <OgCard meta={meta} headline={headline} summary={summary} coverage={coverage} coverageText={coverageText} foot={foot} host={host} kicker="Story" />,
    { ...size, fonts: fonts.length ? fonts : undefined, headers: degraded ? { "cache-control": "no-store" } : undefined },
  );
}
