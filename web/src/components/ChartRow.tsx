"use client";

import Link from "next/link";
import type { FeedItem } from "@/lib/api";
import { CoverageBar, MonogramStack, coverageText, languagesOf } from "@/components/Coverage";
import { relativeTime } from "@/lib/dateline";
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
 * the evidence before the headline. No publisher photograph, ever.
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

  return (
    <li>
      <Link
        href={`/story/${item.id}`}
        aria-current={lastOpened ? "true" : undefined}
        className={`row-card group ${single ? "single" : ""} ${lead ? "px-[18px] py-5" : "px-4 py-3.5"}`}
      >
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
          className={`font-record font-medium text-balance ${lead ? "mt-2 text-[26px] leading-[1.18] sm:text-[30px]" : "mt-1.5 text-[19px] leading-[1.3]"} group-hover:underline group-focus-visible:underline underline-offset-4 decoration-1`}
          style={{ color: "var(--ink)", letterSpacing: "-0.005em" }}
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
        <div className="mt-3 flex min-w-0 flex-wrap items-center gap-x-3 gap-y-2">
          <MonogramStack outlets={outlets} />
          <span className="inline-flex items-center gap-2.5">
            <CoverageBar outlets={outlets} fallbackCount={item.source_count} />
            <span className="whitespace-nowrap font-mono text-[11px] tracking-[0.02em]" style={{ color: "var(--ink-3)" }}>
              {coverageText(outlets, item.source_count)}
            </span>
          </span>
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
