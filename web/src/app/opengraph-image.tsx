import { ImageResponse } from "next/og";

import { PrismMarkSvg } from "@/lib/ogCard";
import { OG_COLORS, OG_DISPLAY, OG_MONO, ogFonts } from "@/lib/ogFonts";
import { SITE_URL } from "@/lib/site";

// The brand card: every route without a card of its own (the landing, the
// chart, a sector, trending, pulse, search) shares this one. The tagline is
// the headline; one sentence says what the product does; nothing is counted
// that the card did not count.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const c = OG_COLORS;
  const headline = "One story. Every perspective.";
  const line = "Every outlet's report of one event, gathered into one story you can check: who said what, verbatim, and which outlets.";
  const host = SITE_URL.replace(/^https?:\/\//, "");
  const fonts = await ogFonts(headline, line, host, "PRISM Today's chart");
  return new ImageResponse(
    (
      <div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column", background: c.ground, color: c.ink, padding: "48px 56px", fontFamily: "Hind, sans-serif" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <PrismMarkSvg size={44} ink={c.ink} />
          <span style={{ fontFamily: OG_DISPLAY, fontSize: 56, letterSpacing: 2, lineHeight: 1 }}>PRISM</span>
        </div>
        <div style={{ display: "flex", flexDirection: "column", flex: 1, justifyContent: "center", paddingBottom: 40 }}>
          <span style={{ fontSize: 76, lineHeight: 1.1, fontWeight: 500, letterSpacing: -1 }}>{headline}</span>
          <span style={{ marginTop: 22, fontSize: 26, lineHeight: 1.45, color: c.inkMuted, maxWidth: 900 }}>{line}</span>
        </div>
        <div style={{ display: "flex", justifyContent: "space-between", borderTop: `1px solid ${c.line}`, paddingTop: 18, fontFamily: OG_MONO, fontSize: 16, color: c.inkMuted, textTransform: "uppercase", letterSpacing: 1 }}>
          <span>Today's chart</span><span>{host}</span>
        </div>
      </div>
    ),
    { ...size, fonts: fonts.length ? fonts : undefined },
  );
}
