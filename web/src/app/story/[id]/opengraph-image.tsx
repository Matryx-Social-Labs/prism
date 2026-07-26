import { ImageResponse } from "next/og";

import { fetchEvent } from "@/lib/api";
import { OG_COLORS, displayStack, ogFonts } from "@/lib/ogFonts";

// Social card for a shared /story/<id> link. Most stories carry no publisher
// photo (image_url is null well over half the time), and without this those
// shares land in WhatsApp as a bare text link. Stories that DO have a photo keep
// it — page.tsx sets openGraph.images and that wins over this file.
// Same constraints as the trending card: monochrome + spectrum accent (color
// means a lens is speaking; this bar is the brand mark), no LLM, Node runtime.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let title = "One story. Every perspective.";
  let sources = 0;
  let sector = "";
  let degraded = false;
  try {
    const e = await fetchEvent(id);
    title = e.title;
    sources = e.sources?.length ?? 0;
    sector = e.sector ?? "";
  } catch {
    // Serving the generic card as a 200 is worse than failing: social scrapers
    // fetch a URL once and cache the preview for days, so one API blip would
    // permanently burn the preview for every story shared during it.
    degraded = true;
  }

  const eyebrow = ["PARSE", sector.replaceAll("_", " "), sources ? `${sources} SOURCES` : ""]
    .filter(Boolean)
    .join(" · ")
    .toUpperCase();
  const headline = title.length > 120 ? `${title.slice(0, 118)}…` : title;
  // Every string the card draws — see ogFonts: an omitted glyph vanishes.
  const fonts = await ogFonts(headline, eyebrow, "One story. Every perspective.");

  return new ImageResponse(
    (
      <div
        style={{
          height: "100%",
          width: "100%",
          display: "flex",
          flexDirection: "column",
          background: OG_COLORS.ground,
          color: OG_COLORS.ink,
          padding: "64px 72px",
          fontFamily: displayStack(headline),
        }}
      >
        {/* Spectrum accent, the one place DESIGN.md still allows a gradient —
            and only as a 2–3px hairline. This was an 8px slab. */}
        <div
          style={{
            height: 3,
            width: "100%",
            background: "linear-gradient(90deg,#F59E0B,#06B6D4,#8B5CF6)",
          }}
        />
        <div
          style={{
            marginTop: 40,
            fontSize: 22,
            letterSpacing: 4,
            color: OG_COLORS.inkMuted,
            fontFamily: "IBM Plex Mono, monospace",
            display: "flex",
          }}
        >
          {eyebrow}
        </div>
        <div style={{ marginTop: 28, fontSize: 58, lineHeight: 1.14, fontWeight: 600, display: "flex" }}>
          {headline}
        </div>
        <div style={{ flex: 1 }} />
        <div style={{ fontSize: 24, color: OG_COLORS.inkFaint, display: "flex" }}>
          One story. Every perspective.
        </div>
      </div>
    ),
    {
      ...size,
      fonts: fonts.length ? fonts : undefined,
      // Don't let a scraper cache a card we built from nothing.
      headers: degraded ? { "cache-control": "no-store" } : undefined,
    },
  );
}
