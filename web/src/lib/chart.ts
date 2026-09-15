import type { FeedItem } from "@/lib/api";

/**
 * The chart: one public list, most-corroborated first.
 *
 * The API returns the window newest-first. The chart's own rule is that the
 * weight of evidence leads — a story eight outlets reported outranks one that
 * one outlet reported five minutes ago — so the order is decided HERE, in one
 * place, and it is the same for every reader (the founder's D2: one page
 * everyone can check). Ties break on recency.
 */
export function chartOrder(items: FeedItem[]): FeedItem[] {
  return [...items].sort((a, b) => {
    if (b.source_count !== a.source_count) return b.source_count - a.source_count;
    const ta = Date.parse(a.latest_published_at ?? a.last_updated_at) || 0;
    const tb = Date.parse(b.latest_published_at ?? b.last_updated_at) || 0;
    return tb - ta;
  });
}

