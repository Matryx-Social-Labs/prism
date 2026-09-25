import { ImageResponse } from "next/og";

import { CARD_TEXT, SITE_HEADLINE, SITE_LINE, SiteCard } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { SITE_URL } from "@/lib/site";

// The brand card, on the ink ground (share cards v3): every route without a
// card of its own shares it, and a card route whose record could not be read
// falls back to it rather than to an invented one.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image() {
  const host = SITE_URL.replace(/^https?:\/\//, "");
  const fonts = await ogFonts(SITE_HEADLINE, SITE_LINE, host, CARD_TEXT);
  return new ImageResponse(<SiteCard headline={SITE_HEADLINE} line={SITE_LINE} host={host} />, { ...size, fonts: fonts.length ? fonts : undefined });
}
