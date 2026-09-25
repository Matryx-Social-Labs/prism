"use client";

import Link from "next/link";
import { Ago } from "@/components/Ago";
import type { FeedItem } from "@/lib/api";
import { CoverageBar, MonogramStack, OutletIcon, coverageText, languagesOf } from "@/components/Coverage";
import { REPORT_IMAGES } from "@/lib/images";
import { HeardOn } from "@/components/Clips";
import { PhotoImg } from "@/components/PhotoImg";
import { langNative } from "@/lib/languages";
import { regionLabel } from "@/lib/regions";
import { sectorGroup } from "@/lib/sectors";

/**
 * The story row — the unit of the product, identical on Today, Stories, Search,
 * Watchlist and the landing (DESIGN.md § Story row). Top to bottom: meta
 * (subject or region · time since the last report · languages), the title in
 * the record voice, what changed, then the foot: outlet monograms, the coverage
 * bar with its count, and the lens dot when the story earns a professional read.
 *
 * A single-source row has a dashed border — the reader sees the thinness of
 * the evidence before the headline.
 *
 * The photograph (founder, 2026-09-20 — a picture is what makes a reader tap
 * one story rather than read every line): the report's own lead image, as a
 * CREDITED thumbnail — the outlet's icon sits on it and the alt says whose it
 * is — on the right of the row, and across the top of the lead on the phone.
 * Hotlinked, never proxied; `NEXT_PUBLIC_REPORT_IMAGES=0` removes every one
 * (DESIGN.md § Images). A row without a picture keeps the same shape.
 */

export type LensMarker = { key: "markets" | "cyber"; className: string; label: string };

/** A paid read exists when the pipeline extracted the facts that lens renders. */
export function lensMarkers(it: FeedItem): LensMarker[] {
  const out: LensMarker[] = [];
  if (it.tickers?.length || it.catalyst) out.push({ key: "markets", className: "l-markets", label: "Markets read" });
  if (it.cve_ids?.length || it.kev_listed || it.cvss_score != null) out.push({ key: "cyber", className: "l-cyber", label: "Cyber read" });
  return out;
}

/** The subject when it has one; the place when it does not. Never "Other". */
export function rowSubject(it: FeedItem, pageCode: string | null): string | null {
  const g = sectorGroup(it.sector);
  if (g && g.code !== pageCode) return g.name;
  if (g) return null;
  return regionLabel(it.regions);
}

export function ChartRow({
  item,
  lead = false,
  lastOpened = false,
  primaryLang = "en",
  pageCode = null,
  draw = false,
}: {
  item: FeedItem;
  lead?: boolean;
  /** The row the reader last opened carries a small mark on return. */
  lastOpened?: boolean;
  primaryLang?: string;
  /** The sector code the whole page is filtered to, omitted from every row's meta. */
  pageCode?: string | null;
  /** Draw the coverage bar in once (a page's hero row only — Design System v2 · Motion). */
  draw?: boolean;
}) {
  const single = item.source_count <= 1;
  const markers = lensMarkers(item);
  const outlets = item.outlets ?? [];
  const subject = rowSubject(item, pageCode);
  const when = item.latest_published_at ?? item.last_updated_at;
  const langs = languagesOf(outlets);
  const langTag = langs.length > 1 ? langs.map((l) => l.toUpperCase()).join("·") : item.headline_lang && item.headline_lang !== primaryLang ? langNative(item.headline_lang) : null;
  const photo = REPORT_IMAGES && item.image_url ? item.image_url : null;
  const credit = item.image_outlet ?? null;
  // The report's own photograph, credited (Design System v2 · StoryRow): across
  // the top of the lead, a 108×80 thumbnail at the right of any other row.
  const thumb = photo && (
    <figure className="p-thumb" style={lead ? { width: "100%", aspectRatio: "16/9" } : { width: 108, height: 80 }}>
      <PhotoImg src={photo} alt={credit ? `Photo: ${credit.name}` : "Photo from a report on this story"} eager={lead} />
      {credit && (
        <figcaption className="p-thumb__credit" title={`Photo: ${credit.name}`}>
          <OutletIcon domain={credit.domain} code={credit.code} name={credit.name} size={16} />
          {lead ? credit.name : null}
        </figcaption>
      )}
    </figure>
  );
  const meta: React.ReactNode[] = [];
  if (subject) meta.push(<span key="s" className="p-meta__subject">{subject}</span>);
  if (when) meta.push(<Ago key="t" iso={when} className="p-meta__prov" />);
  if (langTag) meta.push(<span key="l" className="p-meta__prov">{langTag}</span>);
  if (lastOpened) meta.push(<span key="r" className="p-meta__prov" aria-label="Read">read</span>);

  return (
    <li className={lead ? "sm:col-span-2" : undefined}>
      <Link
        href={`/story/${item.id}`}
        aria-current={lastOpened ? "true" : undefined}
        className={`p-row ${lead ? "p-row--lead" : ""} ${single ? "p-row--single" : ""} h-full`}
        style={{ padding: lead ? "18px 20px 16px" : "14px 16px 12px", gap: 10 }}
      >
        {lead && thumb}
        <div className="flex items-start gap-3.5">
          <div className="grid min-w-0 flex-1 gap-1.5">
            <div className="p-meta">{meta.flatMap((m, i) => (i ? [<span key={`d${i}`} className="p-meta__sep" />, m] : [m]))}</div>
            <h2 className="p-row__title">{item.title}</h2>
            {item.summary && <p className="p-row__sum">{item.summary}</p>}
          </div>
          {!lead && thumb}
        </div>
        {/* The foot wraps rather than truncates: the count is the legend for the
            bar and must never be cut to "3 out…"; the lens dot drops to its own
            line on a narrow phone. */}
        <div className="p-row__foot mt-auto">
          <MonogramStack outlets={outlets} size={24} />
          <span className="inline-flex items-center gap-2.5">
            <CoverageBar outlets={outlets} fallbackCount={item.source_count} draw={draw} />
            <span className="p-count">{single ? "1 outlet · one source so far" : coverageText(outlets, item.source_count)}</span>
          </span>
          <HeardOn shows={item.clip_shows} />
          {markers.map((m) => (
            <span key={m.key} className={`lensdot ${m.className} ml-auto`}>
              <i /> {m.label}
            </span>
          ))}
        </div>
      </Link>
    </li>
  );
}
