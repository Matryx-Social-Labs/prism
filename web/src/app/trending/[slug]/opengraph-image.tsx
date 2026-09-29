import { ImageResponse } from "next/og";

import { fetchSources, fetchTrendingStory } from "@/lib/api";
import { monitoredText } from "@/lib/coverage";
import { CARD_TEXT, SITE_HEADLINE, SITE_LINE, SiteCard, StoryCard, tally } from "@/lib/ogCard";
import { ogFonts } from "@/lib/ogFonts";
import { spanDays } from "@/lib/spine";
import { sectorGroup } from "@/lib/sectors";

// A trending group's card (share cards v3): its status, subject and span, its
// headline, and — for a VERIFIED arc only — the route of its developments; a
// provisional group is related coverage, never a chronology (PRODUCT.md), so
// it gets no route. Then the counted bar.
export const size = { width: 1200, height: 630 };
export const contentType = "image/png";
export const alt = "A developing story's share card on Prism: its name, whether its grouping is verified, how many days it spans, and its coverage bar with how many of the outlets Prism monitors reported it.";

export default async function Image({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const [s, set] = await Promise.all([fetchTrendingStory(slug).catch(() => null), fetchSources()]);
  if (!s) {
    // A generic card served as a 200 would be cached by the scraper for days.
    const fonts = await ogFonts(SITE_HEADLINE, SITE_LINE, CARD_TEXT);
    return new ImageResponse(<SiteCard headline={SITE_HEADLINE} line={SITE_LINE} />, { ...size, fonts: fonts.length ? fonts : undefined, headers: { "cache-control": "no-store" } });
  }
  const verified = s.boundary_status === "verified";
  const t = tally((s.outlets ?? []).map((o) => o.outlet));
  const devs = s.developments.length;
  const days = spanDays(s.developments);
  const dated = s.developments.map((d) => d.occurred_at).filter((x): x is string => !!x);
  const route = verified && dated.length === devs ? dated.sort() : null;
  const meta = [sectorGroup(s.sector)?.name ?? "", days ? `${days} ${days === 1 ? "day" : "days"}` : ""];
  const unit = verified ? (devs === 1 ? "development" : "developments") : devs === 1 ? "record" : "records";
  const count = `${devs} ${unit} · ${monitoredText(t.outlets, set?.outlets)}`;
  const path = `/trending/${slug}`;
  const fonts = await ogFonts(s.label, ...meta, count, path, CARD_TEXT, route ? "JANFEBMARAPRMAYJUNJULAUGSEPTOCTNOVDEC" : "");
  return new ImageResponse(
    <StoryCard
      path={path}
      pill={verified ? { label: "Verified", check: true } : { label: "Grouping under review", dashed: true }}
      meta={meta}
      headline={s.label}
      tally={t}
      count={count}
      route={route}
    />,
    { ...size, fonts: fonts.length ? fonts : undefined },
  );
}
