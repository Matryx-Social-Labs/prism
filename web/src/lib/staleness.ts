import { newsTime } from "@/lib/dateline";

/** Hours without a new report before the chart says so. */
export const STALE_AFTER_HOURS = 12;

/**
 * The newest report behind a set of rows, and whether the chart has gone
 * quiet: when enrichment is paused (a spent LLM balance, an outage) the
 * collectors still run but no new story appears, and a frozen chart that
 * looks current is a lie the masthead should not tell. Returns the ISO stamp
 * of the newest report when it is older than STALE_AFTER_HOURS, else null.
 */
export function staleSince(items: { latest_published_at?: string | null; last_updated_at: string }[], now = Date.now()): string | null {
  const newest = items.map((i) => Date.parse(newsTime(i))).filter((t) => !Number.isNaN(t));
  if (!newest.length) return null;
  const t = Math.max(...newest);
  return now - t > STALE_AFTER_HOURS * 3_600_000 ? new Date(t).toISOString() : null;
}
