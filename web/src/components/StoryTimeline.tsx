"use client";

import Link from "next/link";
import { Corner } from "@/components/icons";
import type { StoryTimelineData } from "@/lib/api";
import { shortDate } from "@/lib/dateline";

// "The story so far" — ONE canonical, chronological timeline of a story's
// developments, identical on every development (they share the same connected
// component). Causal rationale rides inline as a "why" note under the
// development it explains. The section title and hint belong to the caller
// (SectionHead: "All developments", "Related reporting"); this prints the cast
// and the list. Mono for dates and counts (provenance), hairline rules; the rows
// print in (.p-print), instant under reduced motion.
//
// mode="related" is Design System v2 · structure/RelatedStories for a
// provisional grouping: date · title · sources on DASHED rules, because the
// grouping is under review and no order between the rows is claimed.

function dateLabel(iso: string | null): string {
  return iso ? shortDate(iso).toUpperCase() : "";
}

function sources(n: number | undefined): string | null {
  return n == null ? null : `${n} ${n === 1 ? "source" : "sources"}`;
}

export function StoryTimeline({ story, mode = "timeline" }: { story?: StoryTimelineData; mode?: "timeline" | "related" }) {
  const developments = story?.developments ?? [];
  const cast = story?.cast ?? [];
  // A timeline only exists when there's more than just this event.
  if (developments.filter((d) => !d.is_current).length === 0) return null;

  if (mode === "related") {
    return (
      <ol className="p-print">
        {developments.map((n) => (
          <li
            key={n.id}
            className="grid grid-cols-[56px_minmax(0,1fr)] items-baseline gap-x-3 gap-y-1 border-t py-3 sm:grid-cols-[64px_minmax(0,1fr)_auto]"
            style={{ borderTopStyle: "dashed", borderColor: "var(--line-strong)" }}
          >
            <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{dateLabel(n.occurred_at)}</span>
            {n.is_current ? (
              <span style={{ font: "var(--t-title-s)", color: "var(--ink)" }}>
                {n.title} <span className="p-eyebrow ml-1 whitespace-nowrap">You are here</span>
              </span>
            ) : (
              <Link href={`/story/${n.id}`} className="underline-offset-4 hover:underline" style={{ font: "var(--t-title-s)", color: "var(--ink)" }}>
                {n.title}
              </Link>
            )}
            {sources(n.source_count) && <span className="p-count col-start-2 sm:col-start-auto">{sources(n.source_count)}</span>}
          </li>
        ))}
      </ol>
    );
  }

  return (
    <div>
      {cast.length > 0 && (
        <div className="mb-5 flex flex-wrap items-center gap-1.5">
          <span className="mr-1" style={{ font: "var(--t-label)", color: "var(--ink-3)" }}>Following</span>
          {cast.map((name) => (
            <span key={name} className="p-chip">{name}</span>
          ))}
        </div>
      )}

      {/* Timeline: a hairline rule down the left, one dated node per development. */}
      <ol className="p-print relative flex flex-col" style={{ marginLeft: 6 }}>
        <span aria-hidden className="absolute bottom-1 left-0 top-1 w-px" style={{ background: "var(--line)" }} />
        {developments.map((n) => (
          <li key={n.id} className="relative flex gap-4 py-2.5 pl-6">
            {/* marker: filled ink = you are here, hollow = other development */}
            <span
              aria-hidden
              className="absolute left-0 top-[15px] h-[9px] w-[9px] -translate-x-1/2 rounded-full"
              style={n.is_current ? { background: "var(--ink)", border: "2px solid var(--ink)" } : { background: "var(--paper)", border: "1.5px solid var(--line-strong)" }}
            />
            <span className="w-[52px] shrink-0 pt-[3px] font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
              {dateLabel(n.occurred_at)}
            </span>
            <span className="flex min-w-0 flex-col gap-0.5">
              {n.is_current ? (
                <>
                  <span style={{ font: "600 15px/1.4 var(--font-read)", color: "var(--ink)" }}>{n.title}</span>
                  <span className="p-eyebrow">You are here</span>
                </>
              ) : (
                <Link href={`/story/${n.id}`} className="underline-offset-4 hover:underline" style={{ font: "500 15px/1.4 var(--font-read)", color: "var(--ink-2)" }}>
                  {n.title}
                </Link>
              )}
              {n.why && (
                <span className="flex items-start gap-1.5" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
                  <Corner className="mt-[2px] shrink-0" /> {n.why}
                </span>
              )}
              {sources(n.source_count) && <span className="p-count">{sources(n.source_count)}</span>}
            </span>
          </li>
        ))}
      </ol>
    </div>
  );
}
