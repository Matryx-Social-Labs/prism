import { ImageResponse } from "next/og";

import { fetchEvent } from "@/lib/api";
import { OgCard } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { origins, shortDate } from "@/lib/dateline";
import { sectorCode } from "@/lib/sectors";
import { SITE_URL } from "@/lib/site";

// Social card for a shared /story/<id> link: the chart's row at poster scale
// (design 12-share-card). Most stories carry no publisher photo, and without
// this those shares land in WhatsApp as a bare text link; stories that DO have
// a photo keep it — page.tsx sets openGraph.images and that wins. No LLM,
// Node runtime.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let title = "One story. Every perspective.";
  let sources = 0;
  let grid: string[] = [];
  let foot = "";
  let degraded = false;
  try {
    const e = await fetchEvent(id);
    title = e.title;
    sources = e.sources.length;
    const quotes = (e.claims ?? []).reduce((n, s) => n + s.claims.length, 0);
    grid = [origins({ coverage: e.coverage } as Parameters<typeof origins>[0], 2), e.occurred_at ? shortDate(e.occurred_at) : "", sectorCode(e.sector), quotes ? `${quotes} ${quotes === 1 ? "quote" : "quotes"}` : ""].filter(Boolean);
    foot = e.headline_by === "prism" ? `Headline by Prism · from ${sources} ${sources === 1 ? "report" : "reports"}` : `Headline as filed · ${sources} ${sources === 1 ? "report" : "reports"}`;
  } catch {
    // Serving the generic card as a 200 is worse than failing: social scrapers
    // fetch a URL once and cache the preview for days, so one API blip would
    // permanently burn the preview for every story shared during it.
    degraded = true;
  }
  const headline = title.length > 120 ? `${title.slice(0, 118)}…` : title;
  const countLabel = sources ? `${sources} ${sources === 1 ? "outlet" : "outlets"} filed this story` : "";
  const host = SITE_URL.replace(/^https?:\/\//, "");
  // Every string the card draws — see ogFonts: an omitted glyph vanishes.
  const fonts = await ogFonts(headline, countLabel, ...grid, foot, host, "PRISM One story. Every perspective.", String(sources));

  return new ImageResponse(
    <OgCard count={sources || ""} countLabel={countLabel} headline={headline} grid={grid} foot={foot} host={host} />,
    { ...size, fonts: fonts.length ? fonts : undefined, headers: degraded ? { "cache-control": "no-store" } : undefined },
  );
}
