import { ImageResponse } from "next/og";

import { fetchEvent } from "@/lib/api";
import { OgCard } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { shortDate } from "@/lib/dateline";
import { sectorGroup } from "@/lib/sectors";
import { SITE_URL } from "@/lib/site";

// Social card for a shared /story/<id> link: the record's header at poster
// scale (DESIGN.md § Share cards) — meta line, headline, summary, the coverage
// bar in the outlets' slot colours with its count, the headline's provenance.
// No publisher photograph, ever. No LLM, Node runtime.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export const coverageOf = (sources: { origin?: string | null }[]) => {
  const out: Record<"national" | "intl" | "regional" | "wire", number> = { national: 0, intl: 0, regional: 0, wire: 0 };
  for (const s of sources) if (s.origin && s.origin in out) out[s.origin as keyof typeof out] += 1;
  return out;
};

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let headline = "Follow the story, not the headlines.";
  let summary: string | null = null;
  let meta: string[] = [];
  let foot = "";
  let coverage: ReturnType<typeof coverageOf> | undefined;
  let coverageText = "";
  let degraded = false;
  try {
    const e = await fetchEvent(id);
    headline = e.title;
    summary = e.summary;
    const n = e.sources.length;
    const outlets = new Set(e.sources.map((s) => s.publisher ?? s.source_name)).size;
    const langs = new Set(e.sources.map((s) => s.language).filter(Boolean)).size;
    const quotes = (e.claims ?? []).reduce((k, s) => k + s.claims.length, 0);
    meta = [sectorGroup(e.sector)?.name ?? "", e.occurred_at ? shortDate(e.occurred_at) : "", quotes ? `${quotes} ${quotes === 1 ? "quote" : "quotes"}` : ""].filter(Boolean);
    coverage = coverageOf(e.sources);
    coverageText = `${outlets} ${outlets === 1 ? "outlet" : "outlets"} · ${n} ${n === 1 ? "report" : "reports"}${langs > 1 ? ` · ${langs} languages` : ""}`;
    foot = e.headline_by === "prism" ? `Headline by Prism · from ${n} ${n === 1 ? "report" : "reports"}` : "Headline as filed";
  } catch {
    // A generic card served as a 200 would be cached by the scraper for days.
    degraded = true;
  }
  const host = SITE_URL.replace(/^https?:\/\//, "");
  const fonts = await ogFonts(headline, summary ?? "", ...meta, coverageText, foot, host, "Prism");
  return new ImageResponse(
    <OgCard meta={meta} headline={headline} summary={summary} coverage={coverage} coverageText={coverageText} foot={foot} host={host} />,
    { ...size, fonts: fonts.length ? fonts : undefined, headers: degraded ? { "cache-control": "no-store" } : undefined },
  );
}
