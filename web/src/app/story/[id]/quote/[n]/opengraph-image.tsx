import { ImageResponse } from "next/og";

import { fetchEvent } from "@/lib/api";
import { langName } from "@/lib/languages";
import { CARD_TEXT, QuoteCard, SITE_HEADLINE, SITE_LINE, SiteCard, stamp } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { findQuote } from "@/lib/quotes";
import { indexSources } from "@/lib/sources";

// The quote card (PLAN-LAUNCH §6, share cards v3): the sentence as the article
// printed it, who said it, and OUTLET · [n] · DATE · LANGUAGE — the language
// it was PRINTED in, because the verbatim check is against the article, not the
// speaker. The most shared thing on WhatsApp is a sentence. The language is
// printed by its English name: Satori does not shape Indic scripts, so a
// native-script name (the design's हिंदी) comes out with its vowel signs misplaced.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

async function quoteCard(id: string, n: string) {
  const e = await fetchEvent(id);
  const q = findQuote(e.claims, n, e.quote_aliases);
  if (!q) return null;
  const cite = indexSources(e.sources).get(q.claim.article_id);
  const meta = [q.claim.source_name, cite ? `[${cite}]` : "", q.claim.published_at ? stamp(q.claim.published_at) : "", q.claim.lang ? langName(q.claim.lang) : ""];
  const path = `/story/${id}/quote/${q.id}`;
  const fonts = await ogFonts(q.claim.quote_text, q.speaker, q.role ?? "", ...meta, e.title, path, CARD_TEXT);
  return new ImageResponse(
    <QuoteCard path={path} quote={q.claim.quote_text} speaker={q.speaker} role={q.role} meta={meta} translated={q.claim.translated ?? false} reported={q.claim.speech === "reported"} storyTitle={e.title} />,
    { ...size, fonts: fonts.length ? fonts : undefined },
  );
}

export default async function Image({ params }: { params: Promise<{ id: string; n: string }> }) {
  const { id, n } = await params;
  const card = await quoteCard(id, n).catch(() => null);
  if (card) return card;
  // Never a stand-in quote: the brand card, uncached so the real one follows.
  const fonts = await ogFonts(SITE_HEADLINE, SITE_LINE, CARD_TEXT);
  return new ImageResponse(<SiteCard headline={SITE_HEADLINE} line={SITE_LINE} />, { ...size, fonts: fonts.length ? fonts : undefined, headers: { "cache-control": "no-store" } });
}
