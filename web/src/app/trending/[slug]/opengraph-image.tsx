import { ImageResponse } from "next/og";

import { fetchTrendingStory } from "@/lib/api";
import { OgCard } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { shortDate } from "@/lib/dateline";
import { sectorCode } from "@/lib/sectors";
import { SITE_URL } from "@/lib/site";

// The route's share card: the story headline, the count of developments,
// and the shape line (design 12-share-card). No LLM, Node runtime — next/og's
// ImageResponse supports it, and our Vercel "services" deploy rejects Edge
// Function output.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  let label = "Trending on Prism";
  let developments = 0;
  let grid: string[] = [];
  let foot = "";
  let degraded = false;
  let verified = false;
  try {
    const s = await fetchTrendingStory(slug);
    if (!s) throw new Error("no story");
    label = s.label;
    developments = s.developments.length;
    verified = s.boundary_status === "verified";
    const shape = verified ? s.branches?.shape : null;
    grid = [
      `${s.source_count} ${s.source_count === 1 ? "outlet" : "outlets"}`,
      shape ? `${shape.branches} branched off` : "",
      shape ? `${shape.satellites} also reported` : "",
      sectorCode(s.sector),
      s.velocity > 0 ? "moving" : "",
    ].filter(Boolean);
    const first = s.developments[0]?.occurred_at, last = s.developments.at(-1)?.occurred_at;
    foot = verified
      ? `Story headline · from ${developments} ${developments === 1 ? "development" : "developments"}${first && last ? ` · ${shortDate(first)} to ${shortDate(last)}` : ""}`
      : `Provisional grouping · ${developments} related ${developments === 1 ? "event" : "events"} · no chronology implied`;
  } catch {
    degraded = true;
  }
  const headline = label.length > 120 ? `${label.slice(0, 118)}…` : label;
  const countLabel = developments
    ? verified
      ? `${developments} ${developments === 1 ? "development" : "developments"} in this story`
      : `${developments} related ${developments === 1 ? "event" : "events"}`
    : "";
  const host = SITE_URL.replace(/^https?:\/\//, "");
  const fonts = await ogFonts(headline, countLabel, ...grid, foot, host, "PRISM One story. Every perspective.", String(developments));

  return new ImageResponse(
    <OgCard count={developments || ""} countLabel={countLabel} headline={headline} grid={grid} foot={foot} host={host} />,
    { ...size, fonts: fonts.length ? fonts : undefined, headers: degraded ? { "cache-control": "no-store" } : undefined },
  );
}
