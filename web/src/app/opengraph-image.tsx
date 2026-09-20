import { ImageResponse } from "next/og";

import { SiteCard } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { SITE_URL } from "@/lib/site";

// The brand card: every route without a card of its own shares it. The
// promise is the headline; one sentence says what the product does; the
// coverage bar is how a reader learns what Prism is without being told.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const headline = "Follow the story, not the headlines.";
  const line = "One record per story, from monitored outlets across India's languages — every development, verified quote and source open to inspection.";
  const host = SITE_URL.replace(/^https?:\/\//, "");
  const fonts = await ogFonts(headline, line, host, "Prism English national · International · Indian-language");
  return new ImageResponse(<SiteCard headline={headline} line={line} host={host} />, { ...size, fonts: fonts.length ? fonts : undefined });
}
