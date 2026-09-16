"use client";

import Link from "next/link";
import type { FeedItem } from "@/lib/api";
import { istTime, origins } from "@/lib/dateline";
import { langNative } from "@/lib/languages";
import { sectorCode } from "@/lib/sectors";

/**
 * One row of the chart.
 *
 * The chart's grammar, every row the same: the sources count at the left is the
 * row's weight; the headline is the only thing in the reading voice; the label
 * grid beneath is provenance in mono — origin · time · code — in that order,
 * every time. No eyebrow above the headline: the heading carries its own weight
 * (craft floor), and the subject lives in the grid where a chart keeps it.
 *
 * State is line form, never hue. A single-source story sits on a DASHED rule so
 * the reader sees the thinness of the evidence before the headline; nothing is
 * hidden and nothing is coloured. The only colour on the chart is a lens marker:
 * a dot that says a professional reading exists for this row, one tap deep.
 */

export type LensMarker = { key: "markets" | "cyber"; color: string; label: string };

/** A paid read exists when the pipeline extracted the facts that lens renders. */
export function lensMarkers(it: FeedItem): LensMarker[] {
  const out: LensMarker[] = [];
  if (it.tickers?.length || it.catalyst) {
    out.push({ key: "markets", color: "var(--lens-finance)", label: "Markets read" });
  }
  if (it.cve_ids?.length || it.kev_listed || it.cvss_score != null) {
    out.push({ key: "cyber", color: "var(--lens-cyber)", label: "Cyber read" });
  }
  return out;
}

function labelGrid(it: FeedItem, primaryLang: string, pageCode: string | null): string[] {
  const parts: string[] = [];
  const o = origins(it, 2);
  if (o) parts.push(o);
  const t = it.latest_published_at ?? it.last_updated_at;
  if (t) parts.push(istTime(t));
  // On a sector page every row shares the code the strip already shows; a
  // fact that is constant for the whole page is not a fact of the row.
  const code = sectorCode(it.sector);
  if (code && code !== pageCode) parts.push(code);
  if (it.headline_lang && it.headline_lang !== primaryLang) parts.push(langNative(it.headline_lang));
  return parts;
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
  /** The sector code the whole page is filtered to, omitted from every row's grid. */
  pageCode?: string | null;
}) {
  const single = item.source_count <= 1;
  const markers = lensMarkers(item);
  const grid = labelGrid(item, primaryLang, pageCode);
  const count = single ? "1" : String(item.source_count);

  return (
    <li className={single ? "rule-single" : "rule-live"}>
      <Link
        href={`/story/${item.id}`}
        aria-current={lastOpened ? "true" : undefined}
        className={`group grid gap-x-4 ${lead ? "grid-cols-[56px_1fr] py-5" : "grid-cols-[40px_1fr] py-3.5"} focus-visible:outline-none`}
      >
        {/* The weight of the row: how many outlets reported it. */}
        <span
          className={`${lead ? "font-display text-[44px] leading-[0.9] tracking-[-0.01em]" : "font-mono text-[13px] leading-[1.9]"} tabular-nums text-right`}
          style={{ color: single ? "var(--ink-faint)" : "var(--ink)" }}
          aria-label={`${count} ${single ? "source" : "sources"}`}
        >
          {count}
        </span>

        {/* The lead's photo sits above the headline on a phone and beside it from
            lg: a 1100px hero would push the list itself below the fold, and the
            list is the page (THESIS). */}
        <div className={`min-w-0 ${lead && item.image_url ? "lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-x-8" : ""}`}>
          {lead && item.image_url && (
            // eslint-disable-next-line @next/next/no-img-element
            <img
              src={item.image_url}
              alt=""
              className="mb-3 aspect-[16/9] w-full object-cover lg:order-2 lg:mb-0"
              style={{ filter: "grayscale(0.15) contrast(1.02)" }}
              loading="eager"
            />
          )}
          <div className="min-w-0 lg:order-1">
          <h2
            className={`${lead ? "text-[22px] leading-[1.25] sm:text-[26px]" : "text-[15.5px] leading-[1.4]"} font-medium text-balance group-hover:underline group-focus-visible:underline underline-offset-4`}
            style={{ color: "var(--ink)" }}
          >
            {item.title}
            {markers.length > 0 && (
              <span className="ml-2 inline-flex translate-y-[-1px] gap-1 align-middle">
                {markers.map((m) => (
                  <span
                    key={m.key}
                    role="img"
                    aria-label={m.label}
                    className="inline-block h-[7px] w-[7px] rounded-full"
                    style={{ background: m.color }}
                  />
                ))}
              </span>
            )}
          </h2>
          {lead && item.summary && (
            <p className="mt-2 max-w-[36em] text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>
              {item.summary}
            </p>
          )}
          <div
            className="mt-1.5 flex flex-wrap items-baseline gap-x-2.5 font-mono text-[11px] uppercase tracking-[0.04em]"
            style={{ color: "var(--ink-faint)" }}
          >
            {single && <span style={{ color: "var(--ink-muted)" }}>1 source</span>}
            {grid.map((g, i) => (
              <span key={i}>{g}</span>
            ))}
            {lastOpened && (
              <span aria-hidden="true" style={{ color: "var(--ink-muted)" }}>
                · read
              </span>
            )}
          </div>
          </div>
        </div>
      </Link>
    </li>
  );
}
