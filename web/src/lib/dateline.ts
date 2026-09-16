import type { FeedItem } from "@/lib/api";

// Provenance formatting for the desktop ledger rail.
//
// "The Stone" puts every claim about where a story came from in the left margin,
// in mono, so the prose column is never interrupted by chips (DESIGN.md decisions
// log, 2026-07-25). These helpers produce exactly the strings that rail prints.

/** When the NEWS happened, falling back to when Prism last touched the story.
 *
 * `last_updated_at` is set to now() on every projection rebuild, so it records
 * the ingest batch — the feed printed one identical timestamp against every
 * story, and 79% of events were more than six hours from their newest article.
 * DESIGN.md reserves the mono provenance line for claims about where a story
 * came from, so it has to be the news's own clock. The fallback matters for
 * events whose articles carry no published_at at all.
 */
export function newsTime(item: { latest_published_at?: string | null; last_updated_at: string }): string {
  return item.latest_published_at || item.last_updated_at;
}

/** 14:22 IST — the reader's newsroom clock, not their device's. */
export function istTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Kolkata",
  });
}

/** 27 Jul — the provenance line under a quote or a timeline node.
 *  Pinned to IST like istDate: the inline formatter this replaced had no
 *  timeZone, so the same article was dated two ways depending on the reader's
 *  machine, and disagreed with the ledger rail a few pixels away. */
export function shortDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    timeZone: "Asia/Kolkata",
  });
}

/** 05 SEPT 2026 01:25 IST — the ticket's stamp: when the news happened, on the newsroom clock. */
export function istStamp(iso: string): string {
  const d = new Date(iso)
    .toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric", timeZone: "Asia/Kolkata" })
    .replace(/,/g, "")
    .toUpperCase();
  return `${d} ${istTime(iso)} IST`;
}

/** SAT 25 JUL 2026 */
export function istDate(d: Date): string {
  return d
    .toLocaleDateString("en-IN", {
      weekday: "short",
      day: "2-digit",
      month: "short",
      year: "numeric",
      timeZone: "Asia/Kolkata",
    })
    .replace(/,/g, "")
    .toUpperCase();
}

/**
 * "IN ×27 · AE ×3 · UK ×1" — where the coverage physically came from.
 *
 * Ordered by count so the dominant origin reads first, and capped at three: the
 * rail is 104px, and a fourth entry wraps into the headline's optical column.
 */
export function origins(item: FeedItem, max = 3): string {
  const o = item.coverage?.origins ?? {};
  return Object.entries(o)
    .sort((a, b) => b[1] - a[1])
    .slice(0, max)
    .map(([iso, n]) => `${iso} ×${n}`)
    .join(" · ");
}
