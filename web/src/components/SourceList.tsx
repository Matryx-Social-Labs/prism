"use client";

import type { SourceRef } from "@/lib/api";
import { ORIGIN_LABEL, OutletIcon, type Origin } from "@/components/Coverage";
import { relativeTime } from "@/lib/dateline";

/**
 * Publisher images are shown ONLY as link previews to the report they came
 * from — the outlet's own photo, credited, opening the outlet's page — the way
 * search engines and messaging apps preview a link. Never proxied, never used
 * as Prism's own image. A kill switch, because the right to even this much is
 * not settled in India (DESIGN.md § Images; legal note 2026-09-18).
 */
export const REPORT_IMAGES = process.env.NEXT_PUBLIC_REPORT_IMAGES !== "0";

const FUNDING_LABEL: Record<string, string> = {
  state: "State-affiliated",
  public: "Public broadcaster",
};

export function fallbackCode(name: string | null | undefined): string {
  const words = (name ?? "").replace("—", " ").split(/\s+/).filter((w) => w && !/^(the|of|news|&|and)$/i.test(w));
  if (words.length === 0) return "?";
  return (words.length === 1 ? words[0].slice(0, 2) : words.slice(0, 3).map((w) => w[0]).join("")).toUpperCase();
}

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
    <>
      <span className="flex items-center gap-2">
        <OutletIcon domain={s.domain} code={s.code ?? fallbackCode(s.source_name)} name={s.source_name} size={compact ? 24 : 28} />
        <span className="min-w-0 flex-1 truncate text-[12.5px] font-semibold" style={{ color: "var(--ink-2)" }}>{s.source_name}</span>
        {s.published_at && (
          <time dateTime={s.published_at} className="shrink-0 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
            {relativeTime(s.published_at)}
          </time>
        )}
      </span>
      <span className={`mt-2 block font-medium leading-[1.35] [display:-webkit-box] [-webkit-box-orient:vertical] overflow-hidden ${compact ? "text-[13.5px] [-webkit-line-clamp:3]" : "text-[15px] [-webkit-line-clamp:3]"}`} style={{ color: "var(--ink)" }}>
        {s.title}
      </span>
      {(n != null || origin || funding || s.stance) && (
        <span className="mt-2 flex items-center gap-2 text-[11.5px]" style={{ color: "var(--ink-3)" }}>
          {n != null && <span className="font-mono text-[11px]">[{n}]</span>}
          {origin && <span>{origin}</span>}
          {funding && <span>· {funding}</span>}
          {s.stance && <span>· {s.stance}</span>}
        </span>
      )}
    </>
  );
  // The outlet's own photo, badged with the outlet's icon so it never reads as
  // ours; the alt says whose it is.
  const thumb = REPORT_IMAGES && s.image_url && !compact ? (
    <span className="relative h-16 w-16 shrink-0">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={s.image_url} alt={`Photo from ${s.source_name}`} loading="lazy" decoding="async" referrerPolicy="no-referrer" className="h-16 w-16 rounded-[var(--r-sm)] object-cover" style={{ background: "var(--sunken)" }} onError={(e) => { ((e.currentTarget as HTMLImageElement).parentElement as HTMLElement).style.display = "none"; }} />
      <span className="absolute -bottom-1 -right-1"><OutletIcon domain={s.domain} code={s.code ?? fallbackCode(s.source_name)} name={s.source_name} size={20} /></span>
    </span>
  ) : null;
  const cls = `row-card ${thumb ? "flex items-start gap-3" : "block"} ${compact ? "px-3 py-2.5" : "px-4 py-3.5"}`;
  const body = thumb ? (<><span className="min-w-0 flex-1">{inner}</span>{thumb}</>) : inner;
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
    <ul className={`flex flex-col ${compact ? "gap-2" : "gap-2.5"}`}>
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
 * previews — a horizontal scroll on the phone, a strip on desktop. Each tile
 * opens the report it came from and names the outlet on the tile itself, so
 * the photo is never separated from its source. Off when REPORT_IMAGES is off.
 */
export function ReportImages({ sources, limit = 8 }: { sources: SourceRef[]; limit?: number }) {
  if (!REPORT_IMAGES) return null;
  const seen = new Set<string>();
  const withImage = sources.filter((s) => s.image_url && s.url && !seen.has(s.image_url) && seen.add(s.image_url)).slice(0, limit);
  if (withImage.length === 0) return null;
  return (
    <ul className="hide-scroll -mx-5 flex snap-x gap-2.5 overflow-x-auto px-5 sm:-mx-8 sm:px-8 lg:mx-0 lg:grid lg:grid-cols-[repeat(auto-fill,minmax(196px,1fr))] lg:overflow-visible lg:px-0" aria-label="Images from the reports">
      {withImage.map((s) => (
        <li key={s.article_id} className="w-[220px] flex-none snap-start lg:w-auto">
          <a href={s.url!} target="_blank" rel="noopener noreferrer" className="group relative block aspect-[4/3] overflow-hidden rounded-[var(--r-md)] border" style={{ borderColor: "var(--line)", background: "var(--sunken)" }} aria-label={`${s.source_name}: ${s.title}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={s.image_url!} alt={`Photo from ${s.source_name}`} loading="lazy" decoding="async" referrerPolicy="no-referrer" className="h-full w-full object-cover transition-transform duration-300 group-hover:scale-[1.02]" onError={(e) => { ((e.currentTarget as HTMLImageElement).closest("li") as HTMLElement).style.display = "none"; }} />
            {/* The credit, on the image itself. The tile is the link; no badge. */}
            <span className="absolute inset-x-0 bottom-0 flex items-center gap-1.5 px-2.5 pb-2 pt-8 text-[12px] font-semibold text-white" style={{ background: "linear-gradient(to top, rgba(0,0,0,.78) 0%, rgba(0,0,0,.5) 55%, rgba(0,0,0,0) 100%)", textShadow: "0 1px 2px rgba(0,0,0,.5)" }}>
              <OutletIcon domain={s.domain} code={s.code ?? fallbackCode(s.source_name)} name={s.source_name} size={20} />
              <span className="truncate">Photo: {s.source_name}</span>
              {s.published_at && <span className="ml-auto shrink-0 whitespace-nowrap font-mono text-[10.5px] font-normal opacity-90">{relativeTime(s.published_at)}</span>}
            </span>
          </a>
        </li>
      ))}
    </ul>
  );
}

/** One index for [n], shared by the quotes and the report cards. */
export function indexSources(sources: SourceRef[]): Map<string, number> {
  return new Map(sources.map((s, i) => [s.article_id, i + 1]));
}
