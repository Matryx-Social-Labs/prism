import type { EventDetail } from "@/lib/api";

/**
 * The byline under a ticket's headline (founder decision 1b, 2026-09-17):
 * whose words the title is. Prism's headline is written from the reports
 * and says so; otherwise the title is the first report's own headline, and
 * the byline names that outlet so the reader knows they are reading one
 * outlet's words. Every outlet's own headline is under Sources either way.
 */
export function headlineByline(e: Pick<EventDetail, "headline_by" | "sources">): string {
  const n = e.sources.length;
  const reports = `${n} ${n === 1 ? "report" : "reports"}`;
  if (e.headline_by === "prism") return `Headline by Prism · from ${reports}`;
  const first = e.sources[0]?.source_name;
  return first ? `Headline as filed by ${first} · ${reports}` : `Headline as filed · ${reports}`;
}
