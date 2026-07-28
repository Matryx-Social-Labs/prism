import { ImageResponse } from "next/og";

import { fetchTrendingStory } from "@/lib/api";
import { OG_COLORS, displayStack, ogFonts } from "@/lib/ogFonts";

// Auto-generated social card per trending story — the thing that makes a
// forwarded /trending/<slug> link render a premium, on-brand preview (the India
// WhatsApp growth loop). Monochrome + a spectrum accent (color = a lens speaking;
// this bar is the brand mark, not a lens). No LLM. Runs on the default Node.js
// runtime — next/og's ImageResponse supports it, and our Vercel "services" deploy
// rejects Edge Function output.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: { slug: string } }) {
  let label = "Trending on Prism";
  let cast: string[] = [];
  let sources = 0;
  try {
    const s = await fetchTrendingStory(params.slug);
    if (s) {
      label = s.label;
      cast = s.cast.slice(0, 4);
      sources = s.source_count;
    }
  } catch {
    /* fall back to defaults */
  }

  const headline = label.length > 90 ? `${label.slice(0, 88)}…` : label;
  const eyebrow = `PARSE · TRENDING · ${sources} OUTLETS · DEVELOPING`;
  // Every string the card draws — see ogFonts: an omitted glyph vanishes.
  const fonts = await ogFonts(headline, eyebrow, ...cast, "One story. Every perspective.");

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
            textTransform: "uppercase",
            color: OG_COLORS.inkMuted,
            fontFamily: "IBM Plex Mono, monospace",
            display: "flex",
          }}
        >
          {/* No ◮ mark: no loaded face has a glyph for it, so it rendered as a
              tofu box in every share preview. */}
          {eyebrow}
        </div>
        <div style={{ marginTop: 28, fontSize: 62, lineHeight: 1.12, fontWeight: 600, display: "flex" }}>
          {headline}
        </div>
        <div style={{ flex: 1 }} />
        {cast.length > 0 && (
          <div style={{ fontSize: 26, color: OG_COLORS.inkMuted, display: "flex" }}>{cast.join("  ·  ")}</div>
        )}
        <div style={{ marginTop: 20, fontSize: 24, color: OG_COLORS.inkFaint, display: "flex" }}>
          One story. Every perspective.
        </div>
      </div>
    ),
    { ...size, fonts: fonts.length ? fonts : undefined },
  );
}
