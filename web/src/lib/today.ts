import type { FeedItem } from "@/lib/api";
import { bySubject } from "@/lib/archive";
import { chartOrder } from "@/lib/chart";
import { STATE_HUBS } from "@/lib/regions";

/** The most-reported records that lead Today: the lead and the four after it. */
const LEAD_BLOCK = 5;
/** Rows a section shows before it points to where the rest are. */
export const PER_SECTION = 6;

export type TodaySection = { key: string; title: string; href: string | null; items: FeedItem[]; all: FeedItem[]; total: number };
export type TodayLayout = { lead: FeedItem | null; next: FeedItem[]; sections: TodaySection[] };

const inIndia = (it: FeedItem) => !it.regions?.length || it.regions.some((r) => r === "IN" || r.startsWith("IN-"));

/**
 * Today as sections, every record exactly once (2026-11-02: the five most
 * reported printed twice, a card rail and then the head of the list). Most
 * reported first: the lead, the next four, then the reader's state when they
 * have set one, India's records under their subjects in the nav's order, and
 * the world's last. A section shows `perSection` and counts the rest.
 * (Patterns: NYT's and Perplexity's lead block, Apple News's sections; Mobbin.)
 */
export function todaySections(items: FeedItem[], opts: { state: string | null; stateName?: string | null; perSection?: number }): TodayLayout {
  const per = opts.perSection ?? PER_SECTION;
  const ordered = chartOrder(items);
  if (!ordered.length) return { lead: null, next: [], sections: [] };
  const rest = ordered.slice(LEAD_BLOCK);
  const section = (key: string, title: string, href: string | null, all: FeedItem[]): TodaySection => ({ key, title, href, items: all.slice(0, per), all, total: all.length });

  const hub = opts.state ? STATE_HUBS.find((h) => h.code === opts.state) : null;
  const local = hub ? rest.filter((it) => it.regions?.includes(hub.code)) : [];
  const taken = new Set(local.map((it) => it.id));
  const india = rest.filter((it) => !taken.has(it.id) && inIndia(it));
  const world = rest.filter((it) => !taken.has(it.id) && !inIndia(it));

  return {
    lead: ordered[0],
    next: ordered.slice(1, LEAD_BLOCK),
    sections: [
      ...(hub && local.length ? [section("state", opts.stateName ?? hub.name, `/state/${hub.slug}`, local)] : []),
      ...bySubject(india).map((g) => section(g.key ?? "unplaced", g.name, g.href, g.items)),
      ...(world.length ? [section("world", "World", null, world)] : []),
    ],
  };
}
