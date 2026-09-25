import Link from "next/link";
import { ChartRow } from "@/components/ChartRow";
import { OutletIcon } from "@/components/Coverage";
import { ArrowRight } from "@/components/icons";
import type { EventDetail, FeedItem, OutletRef } from "@/lib/api";
import type { Origin } from "@/lib/coverage";
import { fallbackCode, indexSources } from "@/lib/sources";
import { Ago } from "@/components/Ago";

/** Pieces the landing and /about share (Design System v2 · screens/LandingPage). */

/** Registered-source facts from a record's own report list, one per feed (three Mint reports are one outlet). */
export function outletsOf(event: EventDetail | null): OutletRef[] {
  if (!event) return [];
  return event.sources
    .filter((s, i, all) => s.code && s.origin && all.findIndex((t) => t.source_slug === s.source_slug) === i)
    .map((s) => ({ slug: s.source_slug, publisher: s.publisher ?? s.source_slug, name: s.source_name, code: s.code!, origin: s.origin as Origin, language: s.language ?? null, domain: s.domain ?? null }));
}

/** The live lead: a mono "live · updated" strip over the story as the chart's lead row. */
export function LiveLead({ row, outlets }: { row: FeedItem; outlets: OutletRef[] }) {
  return (
    <div className="min-w-0">
      <p className="mb-2.5 flex items-center gap-2">
        <span aria-hidden className="h-2 w-2 rounded-full" style={{ background: "var(--coverage-regional)", animation: "p-pulse 1.6s ease-in-out infinite" }} />
        <span className="p-count uppercase">Live · updated <Ago iso={row.latest_published_at ?? row.last_updated_at} /></span>
      </p>
      <ol aria-label={`Open live record: ${row.title}`}>
        <ChartRow item={{ ...row, outlets: row.outlets?.length ? row.outlets : outlets }} lead />
      </ol>
    </div>
  );
}

/** The record is unreachable: say so, keep the door open. */
export function LiveUnavailable() {
  return (
    <div className="p-card" role="status">
      <p style={{ font: "var(--t-title)" }}>The live record is unavailable right now.</p>
      <p className="mt-2" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>Prism will show current reporting here when the monitored feed reconnects.</p>
      <Link href="/feed" className="p-btn p-btn--secondary mt-4">Try today&rsquo;s record</Link>
    </div>
  );
}

/** What changed: a story's newest reports, newest first, each with its outlet, time and [n]. */
export function ChangeTimeline({ event, shown = 3 }: { event: EventDetail; shown?: number }) {
  const idx = indexSources(event.sources);
  const reports = [...event.sources].sort((a, b) => (b.published_at ?? "").localeCompare(a.published_at ?? "")).slice(0, shown);
  if (reports.length === 0) return null;
  return (
    <div>
      <ol className="grid" aria-label="The newest reports, newest first">
        {reports.map((r, i) => (
          <li key={r.article_id} className="grid grid-cols-[20px_minmax(0,1fr)] gap-3 pb-3.5">
            <span className="relative flex justify-center">
              {i < reports.length - 1 && <span aria-hidden className="absolute -bottom-3.5 top-[18px] w-px" style={{ background: "var(--line-strong)" }} />}
              <span className="relative"><OutletIcon domain={r.domain} code={r.code ?? fallbackCode(r.source_name)} name={r.source_name} size={20} /></span>
            </span>
            <div className="grid min-w-0 gap-0.5">
              <div className="flex flex-wrap items-baseline gap-x-2">
                <span className="text-[13px] font-semibold leading-[1.3]">{r.source_name}</span>
                {r.published_at && <Ago iso={r.published_at} className="p-count" />}
                {idx.has(r.article_id) && <span className="p-count">[{idx.get(r.article_id)}]</span>}
              </div>
              {r.url && /^https?:\/\//.test(r.url) ? (
                <a href={r.url} target="_blank" rel="noopener noreferrer" className="text-[15px] font-medium leading-[1.4] [overflow-wrap:anywhere] hover:underline" style={{ color: "var(--ink)" }}>
                  {r.title} <ArrowRight size={13} className="inline align-[-1px]" />
                </a>
              ) : (
                <span className="text-[15px] font-medium leading-[1.4] [overflow-wrap:anywhere]">{r.title}</span>
              )}
            </div>
          </li>
        ))}
      </ol>
      {event.sources.length > shown && (
        <Link href={`/story/${event.id}`} className="p-btn p-btn--text -ml-1 text-[13.5px]">Show all {event.sources.length} reports</Link>
      )}
    </div>
  );
}
