import { ImageResponse } from "next/og";

import { type EventDetail, fetchEvent, fetchSources, fetchTrendingStory } from "@/lib/api";
import { monitoredText } from "@/lib/coverage";
import { CARD_TEXT, type PillSpec, SITE_HEADLINE, SITE_LINE, SiteCard, StoryCard, stamp, tally } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { sectorGroup } from "@/lib/sectors";

// Social card for a shared /story/<id> link (share cards v3): the record's
// status as its page prints it, the mono meta line, the headline at poster
// scale, the coverage bar in the outlets' slot colours with its counts.
// No publisher photograph, ever. No LLM, Node runtime.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A Prism record's share card: its headline, its status, when it was last updated, and its coverage bar with how many of the outlets Prism monitors reported it.";

/** The pill the story page prints: one source so far, or the arc's boundary once its owner says (StoryView). */
async function statusOf(e: EventDetail, single: boolean): Promise<PillSpec | null> {
  if (single) return { label: "One source so far", dashed: true };
  const arc = e.story_slug ? await fetchTrendingStory(e.story_slug).catch(() => null) : null;
  if (!arc) return null;
  return arc.boundary_status === "verified" ? { label: "Verified record", check: true } : { label: "Provisional grouping", dashed: true };
}

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let e: EventDetail;
  try {
    e = await fetchEvent(id);
  } catch {
    // A generic card served as a 200 would be cached by the scraper for days.
    const fonts = await ogFonts(SITE_HEADLINE, SITE_LINE, CARD_TEXT);
    return new ImageResponse(<SiteCard headline={SITE_HEADLINE} line={SITE_LINE} />, { ...size, fonts: fonts.length ? fonts : undefined, headers: { "cache-control": "no-store" } });
  }
  const t = tally(e.sources.map((s) => ({ publisher: s.publisher ?? s.source_name, origin: s.origin, language: s.language })));
  const single = e.sources.length === 1;
  const pill = await statusOf(e, single);
  // The news's own clock (lib/dateline newsTime): the newest report, not the projection rebuild.
  const newest = e.sources.map((s) => s.published_at).filter((x): x is string => !!x).sort().at(-1) ?? e.last_updated_at;
  // One language is named here; several are counted on the count line, so the
  // mono line never wraps and orphans a code ("· ML") on a multi-language record.
  const meta = [sectorGroup(e.sector)?.name ?? "", single ? stamp(newest) : `Updated ${stamp(newest)}`, ...(t.languages.length === 1 ? [t.languages[0].toUpperCase()] : [])];
  // Out of the monitored set, as the record's header prints it: the record's
  // own denominator, or the public list's for an older payload.
  const monitored = e.monitored_outlets ?? (await fetchSources())?.outlets ?? null;
  const count = single
    ? `${monitoredText(1, monitored)} · the record grows as others report`
    : `${monitoredText(t.outlets, monitored)}${t.languages.length > 1 ? ` · ${t.languages.length} languages` : ""}`;
  const path = `/story/${id}`;
  const fonts = await ogFonts(e.title, ...meta, count, path, CARD_TEXT);
  return new ImageResponse(
    <StoryCard path={path} pill={pill} meta={meta} headline={e.title} tally={t} count={count} single={single} />,
    { ...size, fonts: fonts.length ? fonts : undefined },
  );
}
