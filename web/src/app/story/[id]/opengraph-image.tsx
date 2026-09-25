import { ImageResponse } from "next/og";

import { type EventDetail, fetchEvent, fetchTrendingStory } from "@/lib/api";
import { CARD_TEXT, type PillSpec, SITE_HEADLINE, SITE_LINE, SiteCard, StoryCard, stamp, tally } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { sectorGroup } from "@/lib/sectors";
import { SITE_URL } from "@/lib/site";

// Social card for a shared /story/<id> link (share cards v3): the record's
// status as its page prints it, the mono meta line, the headline at poster
// scale, the coverage bar in the outlets' slot colours with its counts.
// No publisher photograph, ever. No LLM, Node runtime.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";

/** The pill the story page prints: one source so far, or the arc's boundary once its owner says (StoryView). */
async function statusOf(e: EventDetail, single: boolean): Promise<PillSpec | null> {
  if (single) return { label: "One source so far", dashed: true };
  const arc = e.story_slug ? await fetchTrendingStory(e.story_slug).catch(() => null) : null;
  if (!arc) return null;
  return arc.boundary_status === "verified" ? { label: "Verified record", check: true } : { label: "Provisional grouping", dashed: true };
}

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const host = SITE_URL.replace(/^https?:\/\//, "");
  let e: EventDetail;
  try {
    e = await fetchEvent(id);
  } catch {
    // A generic card served as a 200 would be cached by the scraper for days.
    const fonts = await ogFonts(SITE_HEADLINE, SITE_LINE, host, CARD_TEXT);
    return new ImageResponse(<SiteCard headline={SITE_HEADLINE} line={SITE_LINE} host={host} />, { ...size, fonts: fonts.length ? fonts : undefined, headers: { "cache-control": "no-store" } });
  }
  const t = tally(e.sources.map((s) => ({ publisher: s.publisher ?? s.source_name, origin: s.origin, language: s.language })));
  const single = e.sources.length === 1;
  const pill = await statusOf(e, single);
  // The news's own clock (lib/dateline newsTime): the newest report, not the projection rebuild.
  const newest = e.sources.map((s) => s.published_at).filter((x): x is string => !!x).sort().at(-1) ?? e.last_updated_at;
  const meta = [sectorGroup(e.sector)?.name ?? "", single ? stamp(newest) : `Updated ${stamp(newest)}`, ...t.languages.map((l) => l.toUpperCase())];
  const count = single
    ? "1 outlet · the record grows as others report"
    : `${t.outlets} ${t.outlets === 1 ? "outlet" : "outlets"}${t.languages.length > 1 ? ` · ${t.languages.length} languages` : ""}`;
  const address = `${host}/story/${id}`;
  const fonts = await ogFonts(e.title, ...meta, count, address, CARD_TEXT);
  return new ImageResponse(
    <StoryCard address={address} pill={pill} meta={meta} headline={e.title} tally={t} count={count} single={single} />,
    { ...size, fonts: fonts.length ? fonts : undefined },
  );
}
