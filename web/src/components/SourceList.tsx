"use client";

import { Ago } from "@/components/Ago";
import { useRef } from "react";
import type { SourceRef } from "@/lib/api";
import { fallbackCode, indexSources } from "@/lib/sources";

export { fallbackCode, indexSources };
import { ORIGIN_LABEL, OutletIcon, type Origin } from "@/components/Coverage";
import { ArrowLeft, ArrowRight, ArrowUpRight } from "@/components/icons";
import { PhotoImg } from "@/components/PhotoImg";

/** One photo tile: wide enough for "Photo: The Times of India" and a time on one line. */
const TILE_W = 232;
export { hamming } from "@/lib/images";

/**
 * Publisher images are shown ONLY as link previews to the report they came
 * from — the outlet's own photo, credited, opening the outlet's page — the way
 * search engines and messaging apps preview a link. Never proxied, never used
 * as Prism's own image. A kill switch, because the right to even this much is
 * not settled in India (DESIGN.md § Images; legal note 2026-09-18).
 */
import { NEAR_DUPLICATE_BITS, REPORT_IMAGES, hamming } from "@/lib/images";
export { REPORT_IMAGES } from "@/lib/images";

const FUNDING_LABEL: Record<string, string> = {
  state: "State-affiliated",
  public: "Public broadcaster",
};

/**
 * One report as the reader sees it (DESIGN.md § Report card): the outlet's
 * icon and name, when it published, the headline the outlet wrote, and the
 * `[n]` that every quote citing it uses. The whole card opens the article.
 */
export function ReportCard({ source, n, compact = false }: { source: SourceRef; n?: number; compact?: boolean }) {
  const s = source;
  const origin = s.origin ? ORIGIN_LABEL[s.origin as Origin] : null;
  const funding = s.funding ? FUNDING_LABEL[s.funding] : null;
  const inner = (
    <span className="grid min-w-0 flex-1 gap-1.5">
      <span className="flex min-w-0 items-center gap-2">
        <OutletIcon domain={s.domain} code={s.code ?? fallbackCode(s.source_name)} name={s.source_name} size={20} />
        <span className="min-w-0 truncate text-[13px] font-semibold leading-[1.2]" style={{ color: "var(--ink)" }}>{s.source_name}</span>
        {s.published_at && (
          <Ago iso={s.published_at} className="p-count shrink-0" />
        )}
        {n != null && <span className="p-count ml-auto shrink-0 font-mono">[{n}]</span>}
      </span>
      <span
        className="p-row__title block [display:-webkit-box] [-webkit-box-orient:vertical] [-webkit-line-clamp:3] overflow-hidden"
        style={{ font: compact ? "500 14px/1.35 var(--font-read)" : "var(--t-title-s)", color: "var(--ink)", overflowWrap: "anywhere" }}
      >
        {s.title}
        {s.url && <ArrowUpRight size={13} className="ml-1 inline align-[-1px]" />}
      </span>
      {!compact && (origin || funding) && (
        <span className="text-[12px]" style={{ color: "var(--ink-3)" }}>
          {origin}
          {funding && <>{origin ? " · " : ""}{funding}</>}
        </span>
      )}
    </span>
  );
  // The outlet's own photo, credited by the outlet's name beside it, so it
  // never reads as ours; the alt says whose it is.
  const thumb = REPORT_IMAGES && s.image_url && !compact ? (
    <span className="p-thumb h-[72px] w-24 shrink-0" onErrorCapture={(e) => { (e.currentTarget as HTMLElement).style.display = "none"; }}>
      <PhotoImg src={s.image_url} alt={`Photo from ${s.source_name}`} />
    </span>
  ) : null;
  const cls = `p-row ${thumb ? "!flex-row items-start gap-3" : "gap-1.5"} ${compact ? "px-3 py-2.5" : "px-4 py-3.5"}`;
  const body = <>{inner}{thumb}</>;
  return s.url ? (
    <a href={s.url} target="_blank" rel="noopener noreferrer" className={cls} aria-label={`${s.source_name}: ${s.title}`}>
      {body}
    </a>
  ) : (
    <span className={cls}>{body}</span>
  );
}

/**
 * The reports behind a story as cards. `compact` is the desktop rail's
 * variant; both carry `[n]`, the same index the quotes cite.
 */
export function SourceList({
  sources,
  sourceIndex,
  compact = false,
}: {
  sources: SourceRef[];
  sourceIndex: Map<string, number>;
  compact?: boolean;
}) {
  return (
    <ul className={`p-print grid ${compact ? "gap-2" : "gap-2.5"}`}>
      {sources.map((s, i) => (
        <li key={s.article_id ?? `${s.source_name}-${i}`}>
          <ReportCard source={s} n={sourceIndex.get(s.article_id)} compact={compact} />
        </li>
      ))}
    </ul>
  );
}

/**
 * "From the reports": the outlets' own photographs as a rail of credited link
 * previews — one horizontal strip at every width (a grid of eight tall tiles
 * pushed the record off the first screen, 2026-09-20). Snap-scrolls on touch;
 * on desktop a label names the rail and prev/next step it one tile, because a
 * hidden scrollbar gives a mouse no hint. Each tile opens the report it came
 * from and names the outlet on the tile itself, so the photo is never
 * separated from its source. Off when REPORT_IMAGES is off.
 */
export function ReportImages({ sources, limit = 8 }: { sources: SourceRef[]; limit?: number }) {
  const rail = useRef<HTMLUListElement>(null);
  if (!REPORT_IMAGES) return null;
  const seen = new Set<string>();
  const hashes: string[] = [];
  // Same URL, or the same picture under another URL (BBC uploads one photo per
  // language edition): a perceptual hash within a few bits is the same photo.
  const all = sources.filter((s) => {
    if (!s.image_url || !s.url || seen.has(s.image_url)) return false;
    seen.add(s.image_url);
    if (s.image_phash) {
      if (hashes.some((h) => hamming(h, s.image_phash!) <= NEAR_DUPLICATE_BITS)) return false;
      hashes.push(s.image_phash);
    }
    return true;
  });
  // One photo per publisher first, then the rest: BBC's Tamil, Telugu and
  // Bengali editions each upload the same picture under a new id, and three
  // of them in a row read as a repeat before any other outlet gets a tile.
  const firstOf = new Set<string>();
  const lead = all.filter((s) => { const k = s.publisher ?? s.source_name; return firstOf.has(k) ? false : (firstOf.add(k), true); });
  const withImage = [...lead, ...all.filter((s) => !lead.includes(s))].slice(0, limit);
  if (withImage.length === 0) return null;
  const step = (dir: 1 | -1) => rail.current?.scrollBy({ left: dir * (TILE_W + 10), behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
  return (
    <div>
      <div className="mb-2 flex items-center justify-between">
        <p className="font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
          From the reports · {withImage.length} {withImage.length === 1 ? "photo" : "photos"}
        </p>
        {withImage.length > 2 && (
          <span className="hidden items-center gap-1 lg:inline-flex">
            <button type="button" className="icon-btn h-7 w-7" aria-label="Previous photos" onClick={() => step(-1)}><ArrowLeft size={14} /></button>
            <button type="button" className="icon-btn h-7 w-7" aria-label="Next photos" onClick={() => step(1)}><ArrowRight size={14} /></button>
          </span>
        )}
      </div>
      <ul
        ref={rail}
        className="hide-scroll -mx-5 flex snap-x gap-2.5 overflow-x-auto px-5 scroll-pl-5 sm:-mx-8 sm:px-8 sm:scroll-pl-8 lg:mx-0 lg:px-0 lg:scroll-pl-0"
        aria-label="Images from the reports"
      >
        {withImage.map((s) => (
          <li key={s.article_id} className="flex-none snap-start" style={{ width: TILE_W }}>
            <a href={s.url!} target="_blank" rel="noopener noreferrer" className="group relative block aspect-[4/3] overflow-hidden rounded-[var(--r-md)] border" style={{ borderColor: "var(--line)", background: "var(--sunken)" }} aria-label={`${s.source_name}: ${s.title}`}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={s.image_url!} alt={`Photo from ${s.source_name}`} loading="lazy" decoding="async" referrerPolicy="no-referrer" className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]" onError={(e) => { ((e.currentTarget as HTMLImageElement).closest("li") as HTMLElement).style.display = "none"; }} />
              {/* The credit, on the image itself. The tile is the link; no badge. */}
              <span className="absolute inset-x-0 bottom-0 flex items-center gap-1.5 px-2.5 pb-2 pt-8 text-[12px] font-semibold text-white" style={{ background: "linear-gradient(to top, rgba(0,0,0,.78) 0%, rgba(0,0,0,.5) 55%, rgba(0,0,0,0) 100%)", textShadow: "0 1px 2px rgba(0,0,0,.5)" }}>
                <OutletIcon domain={s.domain} code={s.code ?? fallbackCode(s.source_name)} name={s.source_name} size={20} />
                <span className="truncate">Photo: {s.source_name}</span>
                {s.published_at && <Ago iso={s.published_at} className="ml-auto shrink-0 whitespace-nowrap font-mono text-[10.5px] font-normal opacity-90" />}
              </span>
            </a>
          </li>
        ))}
      </ul>
    </div>
  );
}

