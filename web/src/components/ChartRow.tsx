"use client";

import Link from "next/link";
import type { FeedItem } from "@/lib/api";
import { CoverageBar, MonogramStack, OutletIcon, coverageText, languagesOf } from "@/components/Coverage";
import { REPORT_IMAGES } from "@/lib/images";
import { relativeTime } from "@/lib/dateline";
import { HeardOn } from "@/components/Clips";
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
}: {
  item: FeedItem;
  lead?: boolean;
  /** The row the reader last opened carries a small mark on return. */
  lastOpened?: boolean;
  primaryLang?: string;
  /** The sector code the whole page is filtered to, omitted from every row's meta. */
  pageCode?: string | null;
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
  const thumb = photo && (
    <figure className={`relative shrink-0 overflow-hidden rounded-[8px] ${lead ? "aspect-[16/10] w-full lg:aspect-[4/3] lg:w-[260px]" : "h-[76px] w-[104px] sm:h-[84px] sm:w-[124px]"}`} style={{ background: "var(--sunken)" }}>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={photo} alt={credit ? `Photo: ${credit.name}` : "Photo from a report on this story"} loading={lead ? "eager" : "lazy"} decoding="async" referrerPolicy="no-referrer" className="h-full w-full object-cover" />
      {credit && (
        <span className="absolute bottom-1 left-1 rounded-full" style={{ boxShadow: "0 0 0 1.5px var(--surface)" }} title={`Photo: ${credit.name}`}>
          <OutletIcon domain={credit.domain} code={credit.code} name={credit.name} size={lead ? 22 : 18} />
        </span>
      )}
    </figure>
  );

  return (
    <li className={lead ? "2xl:col-span-2" : undefined}>
      <Link
        href={`/story/${item.id}`}
        aria-current={lastOpened ? "true" : undefined}
        className={`story-row row-card group flex h-full flex-col ${single ? "single" : ""} ${lead ? "story-row-lead px-[18px] py-5" : "px-4 py-3.5"}`}
      >
        {/* The words beside the picture (the lead: picture above on the phone,
            beside on a desk); the foot under both, full width. */}
        <div className={photo ? (lead ? "flex flex-col gap-4 lg:flex-row-reverse lg:items-start" : "flex items-start gap-3.5") : ""}>
        {thumb}
        <div className="min-w-0 flex-1">
        <div className="meta-line">
          {subject && <span style={{ color: "var(--ink-2)", fontWeight: 500 }}>{subject}</span>}
          {subject && <span className="dot" />}
          {when && <time dateTime={when}>{relativeTime(when)}</time>}
          {langTag && (
            <>
              <span className="dot" />
              <span>{langTag}</span>
            </>
          )}
          {lastOpened && (
            <>
              <span className="dot" />
              <span aria-label="Read">read</span>
            </>
          )}
        </div>
        <h2
          className={`font-record font-bold text-balance ${lead ? "mt-2 text-[26px] leading-[1.22] sm:text-[30px]" : "mt-1.5 text-[18px] leading-[1.4]"} group-hover:underline group-focus-visible:underline underline-offset-4 decoration-1`}
          style={{ color: "var(--ink)" }}
        >
          {item.title}
        </h2>
        {item.summary && (
          <p
            className={`mt-1 ${lead ? "text-[16px] leading-[1.5] [-webkit-line-clamp:3]" : "text-[14.5px] leading-[1.5] [-webkit-line-clamp:2]"} [display:-webkit-box] [-webkit-box-orient:vertical] overflow-hidden`}
            style={{ color: "var(--ink-2)" }}
          >
            {item.summary}
          </p>
        )}
        {/* The foot wraps rather than truncates: the count is the legend for the
            bar and must never be cut to "3 out…"; the lens dot drops to its own
            line on a narrow phone. */}
        </div>
        </div>
        <div className="mt-auto flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2 pt-3">
          <MonogramStack outlets={outlets} />
          <span className="inline-flex items-center gap-2.5">
            <CoverageBar outlets={outlets} fallbackCount={item.source_count} />
            <span className="whitespace-nowrap font-mono text-[11px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
              {coverageText(outlets, item.source_count)}
            </span>
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
