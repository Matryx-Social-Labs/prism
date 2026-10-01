"use client";

import Link from "next/link";
import { useState } from "react";
import { Corner } from "@/components/icons";
import type { StoryDevelopment, StoryTimelineData } from "@/lib/api";
import { istTime, reportedAt, shortDate } from "@/lib/dateline";

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
//
// Both list the developments in the order they were first reported (the API
// sorts on first_published_at), grouped by day: the gutter prints the day on
// the first development of each day, and every development's time under it.

type Gutter = { at: string | null; day: string; time: string };

/** The gutter of each row: the IST day where it changes, and the first report's time. */
function gutters(developments: StoryDevelopment[]): Gutter[] {
  let prev = "";
  return developments.map((n) => {
    const at = reportedAt(n);
    const day = at ? shortDate(at).toUpperCase() : "";
    const first = day !== prev;
    prev = day;
    // occurred_at alone is a bare date (an older payload): no time to print.
    return { at, day: first ? day : "", time: n.first_published_at ? istTime(n.first_published_at) : "" };
  });
}

function When({ g, className = "" }: { g: Gutter; className?: string }) {
  return (
    <time dateTime={g.at ?? undefined} className={`grid font-mono text-[11px] leading-[1.4] ${className}`} style={{ color: "var(--ink-3)" }}>
      {g.day && <span>{g.day}</span>}
      {g.time && <span>{g.time}</span>}
    </time>
  );
}

function sources(n: number | undefined): string | null {
  return n == null ? null : `${n} ${n === 1 ? "source" : "sources"}`;
}

// What kind of development each record is in its story — the judge's fixed list
// (correlation/verify.FACETS), in this order on every story.
const FACETS: [string, string][] = [
  ["event", "The event"], ["investigation", "Investigation"], ["response", "Response"], ["diplomacy", "Diplomacy"],
  ["people", "People"], ["reactions", "Reactions"], ["politics", "Politics"], ["impact", "Impact"],
  ["explainer", "Explainers"],
];

/** Chips that narrow the list to one kind of development, counted; absent below two kinds. */
function FacetChips({ developments, chosen, choose }: {
  developments: StoryDevelopment[]; chosen: string | null; choose: (facet: string | null) => void;
}) {
  const counts = new Map<string, number>();
  for (const d of developments) if (d.facet) counts.set(d.facet, (counts.get(d.facet) ?? 0) + 1);
  const present = FACETS.filter(([key]) => counts.has(key));
  if (present.length < 2) return null;
  return (
    <div role="group" aria-label="Kinds of development" className="mb-4 flex flex-wrap gap-1.5">
      <button type="button" className="p-chip" aria-pressed={chosen === null} onClick={() => choose(null)}>
        All <span className="p-count">{developments.length}</span>
      </button>
      {present.map(([key, label]) => (
        <button key={key} type="button" className="p-chip" aria-pressed={chosen === key} onClick={() => choose(key)}>
          {label} <span className="p-count">{counts.get(key)}</span>
        </button>
      ))}
    </div>
  );
}

export function StoryTimeline({ story, mode = "timeline" }: { story?: StoryTimelineData; mode?: "timeline" | "related" }) {
  const [facet, setFacet] = useState<string | null>(null);
  const all = story?.developments ?? [];
  const cast = story?.cast ?? [];
  // A timeline only exists when there's more than just this event.
  if (all.filter((d) => !d.is_current).length === 0) return null;

  const developments = facet ? all.filter((d) => d.facet === facet) : all;
  const when = gutters(developments);
  const chips = <FacetChips developments={all} chosen={facet} choose={setFacet} />;

  if (mode === "related") {
    return (
      <>
      {chips}
      <ol className="p-print">
        {developments.map((n, i) => (
          <li
            key={n.id}
            className="grid grid-cols-[56px_minmax(0,1fr)] items-baseline gap-x-3 gap-y-1 border-t py-3 sm:grid-cols-[64px_minmax(0,1fr)_auto]"
            style={{ borderTopStyle: "dashed", borderColor: "var(--line-strong)" }}
          >
            <When g={when[i]} />
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
      </>
    );
  }

  return (
    <div>
      {chips}
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
        {developments.map((n, i) => (
          <li key={n.id} className="relative flex gap-4 py-2.5 pl-6">
            {/* marker: filled ink = you are here, hollow = other development */}
            <span
              aria-hidden
              className="absolute left-0 top-[15px] h-[9px] w-[9px] -translate-x-1/2 rounded-full"
              style={n.is_current ? { background: "var(--ink)", border: "2px solid var(--ink)" } : { background: "var(--paper)", border: "1.5px solid var(--line-strong)" }}
            />
            <When g={when[i]} className="w-[52px] shrink-0 content-start pt-[3px]" />
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
