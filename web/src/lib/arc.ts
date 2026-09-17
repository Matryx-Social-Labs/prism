import type { TrendingStory } from "@/lib/api";

/**
 * How a row on the chart of arcs reads a story's clock.
 *
 * SPAN is whole days between first sighting and last movement (0 for a story
 * that began today). A story is STALE when it has not moved in three days:
 * the row keeps its place but prints on a half-weight rule, the way the chart
 * marks a train that has not been updated. Both come from the story's own
 * timestamps; a story without them reports neither, rather than 0.
 */
export const STALE_AFTER_MS = 3 * 24 * 60 * 60 * 1000;

export function spanDays(s: Pick<TrendingStory, "first_seen_at" | "last_updated_at">): number | null {
  if (!s.first_seen_at || !s.last_updated_at) return null;
  const ms = Date.parse(s.last_updated_at) - Date.parse(s.first_seen_at);
  return Number.isFinite(ms) ? Math.max(0, Math.floor(ms / 86_400_000)) : null;
}

export function isStale(s: Pick<TrendingStory, "last_updated_at">, now = Date.now()): boolean {
  if (!s.last_updated_at) return false;
  const t = Date.parse(s.last_updated_at);
  return Number.isFinite(t) && now - t > STALE_AFTER_MS;
}

/** Verified arcs open on their hero's route. Provisional groups open on the
 * group page, whose copy explicitly refuses to imply chronology. */
export function arcHref(s: Pick<TrendingStory, "hero_event_id" | "slug" | "boundary_status">): string {
  return s.boundary_status === "verified" && s.hero_event_id
    ? `/story/${s.hero_event_id}#route`
    : `/trending/${s.slug}`;
}
