import { ImageResponse } from "next/og";

import { fetchEvent } from "@/lib/api";
import { shortDate } from "@/lib/dateline";
import { QuoteCard } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { findQuote } from "@/lib/quotes";
import { SITE_URL } from "@/lib/site";

// The quote card (PLAN-LAUNCH §6): a verbatim sentence, who said it, the
// outlet that printed it. The most shared thing on WhatsApp is a sentence.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

export default async function Image({ params }: { params: Promise<{ id: string; n: string }> }) {
  const { id, n } = await params;
  const host = SITE_URL.replace(/^https?:\/\//, "");
  let quote = "Follow the story, not the headlines.";
  let speaker = "Prism";
  let role: string | null = null;
  let outlet = "";
  let when: string | null = null;
  let storyTitle: string | null = null;
  let degraded = false;
  try {
    const e = await fetchEvent(id);
    const q = findQuote(e.claims, n);
    if (!q) throw new Error("no such quote");
    quote = q.claim.quote_text;
    speaker = q.speaker;
    role = q.role;
    outlet = q.claim.source_name;
    when = q.claim.published_at ? shortDate(q.claim.published_at) : null;
    storyTitle = e.title;
  } catch {
    degraded = true;
  }
  const fonts = await ogFonts(quote, speaker, role ?? "", outlet, when ?? "", storyTitle ?? "", host, "Prism Who said what Verbatim");
  return new ImageResponse(
    <QuoteCard quote={quote} speaker={speaker} role={role} outlet={outlet} when={when} host={host} storyTitle={storyTitle} />,
    { ...size, fonts: fonts.length ? fonts : undefined, headers: degraded ? { "cache-control": "no-store" } : undefined },
  );
}
