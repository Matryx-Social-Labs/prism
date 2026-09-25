"use client";

import Link from "next/link";
import { Ago } from "@/components/Ago";
import type { FeedItem } from "@/lib/api";
import { CoverageBar, OutletIcon, coverageText, languagesOf } from "@/components/Coverage";
import { lensMarkers, rowSubject } from "@/components/ChartRow";
import { PhotoImg } from "@/components/PhotoImg";
import { REPORT_IMAGES } from "@/lib/images";

/**
 * A story as a card, for rails and grids (Design System v2 · screens/Cards.jsx):
 * the report's credited photograph, the meta line, the headline, the coverage bar,
 * and the lens dot when the story earns a professional read. One source so far
 * draws the card dashed. A story without a photograph keeps the same card, no image.
 */
export function StoryCard({ item, width, big = false }: { item: FeedItem; width?: number | string; big?: boolean }) {
  const outlets = item.outlets ?? [];
  const single = item.source_count <= 1;
  const photo = REPORT_IMAGES && item.image_url ? item.image_url : null;
  const credit = item.image_outlet ?? null;
  const lens = lensMarkers(item)[0];
  const subject = rowSubject(item, null);
  const when = item.latest_published_at ?? item.last_updated_at;
  const langs = languagesOf(outlets);
  const meta = [subject && <span key="s" className="p-meta__subject">{subject}</span>, when && <Ago key="t" iso={when} className="p-meta__prov" />, langs.length > 1 && <span key="l" className="p-meta__prov">{langs.map((l) => l.toUpperCase()).join("·")}</span>].filter(Boolean);
  return (
    <Link
      href={`/story/${item.id}`}
      className="sc-card"
      style={{ width, borderStyle: single ? "dashed" : "solid", borderColor: single ? "var(--line-strong)" : undefined }}
    >
      {photo && (
        <div className="p-thumb" style={{ aspectRatio: big ? "16/9" : "3/2", borderRadius: 0 }}>
          <PhotoImg src={photo} alt={credit ? `Photo: ${credit.name}` : "Photo from a report on this story"} />
          {credit && (
            <span className="p-thumb__credit">
              <OutletIcon domain={credit.domain} code={credit.code} name={credit.name} size={16} />
              {credit.name}
            </span>
          )}
          {lens && (
            <span className="absolute right-1.5 top-1.5 rounded-[2px] px-2 py-1" style={{ background: "color-mix(in srgb, var(--paper) 92%, transparent)" }}>
              <span className={`lensdot ${lens.className}`}><i /> {lens.label}</span>
            </span>
          )}
        </div>
      )}
      <div className="grid flex-1 content-start gap-2 px-3.5 pb-3.5 pt-3">
        <div className="p-meta">{meta.flatMap((m, i) => (i ? [<span key={`d${i}`} className="p-meta__sep" />, m] : [m]))}</div>
        <h3 className="sc-h" style={big ? { font: "var(--t-display-m)" } : undefined}>{item.title}</h3>
        <div className="mt-auto flex flex-wrap items-center gap-2.5 pt-1">
          <CoverageBar outlets={outlets} fallbackCount={item.source_count} width={big ? 200 : 96} />
          <span className="p-count">{single ? "1 outlet · one source so far" : coverageText(outlets, item.source_count)}</span>
          {!photo && lens && <span className={`lensdot ${lens.className} ml-auto`}><i /> {lens.label}</span>}
        </div>
      </div>
    </Link>
  );
}
