import type { FeedItem } from "@/lib/api";

// Provenance formatting for the desktop ledger rail.
//
// "The Stone" puts every claim about where a story came from in the left margin,
// in mono, so the prose column is never interrupted by chips (DESIGN.md decisions
// log, 2026-07-25). These helpers produce exactly the strings that rail prints.

/** 14:22 IST — the reader's newsroom clock, not their device's. */
export function istTime(iso: string): string {
  return new Date(iso).toLocaleTimeString("en-IN", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
    timeZone: "Asia/Kolkata",
  });
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

/** Summed origins across a band, for the band's rail. */
export function bandOrigins(items: FeedItem[], max = 2): string {
  const total: Record<string, number> = {};
  for (const i of items) {
    for (const [iso, n] of Object.entries(i.coverage?.origins ?? {})) {
      total[iso] = (total[iso] ?? 0) + n;
    }
  }
  return Object.entries(total)
    .sort((a, b) => b[1] - a[1])
    .slice(0, max)
    .map(([iso, n]) => `${iso} ×${n}`)
    .join(" · ");
}

/** The most recent update in a band — "last moved 13:05". */
export function lastMoved(items: FeedItem[]): string {
  const newest = items
    .map((i) => i.last_updated_at)
    .sort()
    .at(-1);
  return newest ? istTime(newest) : "";
}

export type Band = { sector: string; items: FeedItem[] };

/**
 * Group the feed into sector bands, densest first.
 *
 * `perBand` matches the design's four-across row exactly; a band that can't fill
 * it is dropped rather than rendered ragged, because a half-empty band reads as
 * a loading state on a 1240px field.
 */
export function bands(items: FeedItem[], exclude: Set<string>, perBand = 4, max = 4): Band[] {
  const bySector = new Map<string, FeedItem[]>();
  for (const i of items) {
    if (exclude.has(i.id) || !i.sector) continue;
    const list = bySector.get(i.sector) ?? [];
    list.push(i);
    bySector.set(i.sector, list);
  }
  return [...bySector.entries()]
    .filter(([, list]) => list.length >= perBand)
    .sort((a, b) => b[1].length - a[1].length)
    .slice(0, max)
    .map(([sector, list]) => ({ sector, items: list.slice(0, perBand) }));
}

/** "POLITICS · ENERGY" — the lead's sector eyebrow. */
export function sectorEyebrow(item: FeedItem): string {
  return [item.sector, item.subsector]
    .filter(Boolean)
    .map((s) => s!.replaceAll("_", " "))
    .join(" · ")
    .toUpperCase();
}
