import type { EventDetail } from "@/lib/api";
import { istStamp, origins } from "@/lib/dateline";
import { sectorCode } from "@/lib/sectors";

/**
 * The ticket's header strip: `BIZ · 8 SOURCES · IN ×6 · US ×2 · 05 SEPT 2026 01:25 IST`.
 *
 * Every fact on it is counted or read off the record — the subject code, how
 * many outlets filed, where from, and when the newest of them published. The
 * same strip heads the phone ticket and re-inks nothing: it is the part of the
 * page that is true whichever lens is reading.
 */
export function ticketFacts(event: EventDetail): string[] {
  const n = event.sources.length;
  const newest = event.sources
    .map((s) => s.published_at)
    .filter((t): t is string => Boolean(t))
    .sort()
    .at(-1);
  const when = newest ?? event.occurred_at ?? event.last_updated_at;
  return [
    sectorCode(event.sector),
    `${n} ${n === 1 ? "source" : "sources"}`,
    origins({ coverage: event.coverage } as Parameters<typeof origins>[0], 3),
    istStamp(when),
  ].filter(Boolean);
}
