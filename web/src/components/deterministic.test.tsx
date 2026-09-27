import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";
import { ChartRow } from "@/components/ChartRow";
import { StoriesPage } from "@/components/StoriesPage";
import { StoryView } from "@/components/StoryView";
import { StoryArc } from "@/components/reading/StoryArc";
import type { EventDetail, FeedItem, TrendingStory, TrendingStoryDetail } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn(), replace: vi.fn() }), usePathname: () => "/", useSearchParams: () => new URLSearchParams() }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []), fetchTrending: vi.fn(async () => []) };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [{ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }],
  lensMeta: () => ({ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }),
}));

/**
 * A cached page must be the same bytes every time it is rendered. Vercel skips
 * the cache write only when a refresh produced identical output, and the pages
 * printed "12m ago" on the server, so every refresh of an unchanged record would
 * have been a paid write (caching plan, 2026-09-27). This renders what the
 * server renders — the story view, a story's arc, a chart row, the stories list —
 * at two moments half an hour apart on one IST day, and requires the same HTML.
 *
 * Deliberately coarser clocks are allowed: the dateline's day, the 12-hour
 * "quiet since" note and the 3-day stale mark change output at most once a day.
 */
const T0 = new Date("2026-09-27T04:30:00Z"); // 10:00 IST
const LATER = new Date("2026-09-27T05:00:00Z"); // 10:30 IST
const minutesBefore = (m: number) => new Date(T0.getTime() - m * 60_000).toISOString();

const EVENT = {
  id: "e1", title: "A story", summary: "Mumbai Police questioned Asha Rao.", sector: "politics", subsector: null,
  image_url: null, regions: [], occurred_at: "2026-09-27", last_updated_at: minutesBefore(12),
  projection: {}, lens_briefs: { reader: "The reader take." }, lens_points: {}, available_lenses: ["reader"],
  coverage: null, perspectives: [], impacts: [],
  entities: [{ name: "Mumbai Police", entity_type: "organization", role: "actor", slug: "mumbai-police", indexable: true }],
  sources: [
    { article_id: "a1", source_name: "The Hindu", source_slug: "the_hindu", url: "https://x.test/a", title: "Report one", published_at: minutesBefore(20), funding: null },
    { article_id: "a2", source_name: "Aaj Tak", source_slug: "aajtak", url: "https://x.test/b", title: "Report two", published_at: minutesBefore(90), funding: null },
  ],
  claims: [{ speaker: "Asha Rao", role: null, claims: [{ quote_text: "We will cooperate.", source_name: "The Hindu", url: "https://x.test/a", published_at: minutesBefore(20) }] }],
} as unknown as EventDetail;

const ROW = {
  id: "e1", title: "A story", headline_lang: null, available_languages: [], summary: null, sector: "politics", subsector: null,
  regions: ["IN"], image_url: null, source_count: 2, last_updated_at: minutesBefore(12), latest_published_at: minutesBefore(20), outlets: [],
} as unknown as FeedItem;

const STORY = {
  slug: "s", canonical_slug: "s", label: "A story", sector: "politics", source_count: 3, velocity: 1,
  boundary_status: "provisional", branches: null, related: [], photos: [], outlets: [], cast: [], cast_refs: [],
  first_seen_at: minutesBefore(600), last_updated_at: minutesBefore(15), shared_cast: [], causal: false,
  developments: [
    { id: "d1", title: "First", sector: "politics", occurred_at: minutesBefore(600), image_url: null, is_current: false, why: null },
    { id: "d2", title: "Latest", sector: "politics", occurred_at: minutesBefore(15), image_url: null, is_current: true, why: null },
  ],
} as unknown as TrendingStoryDetail;

// The arc prints no times yet (audit S4, caching plan phase 5); it is here so it
// stays deterministic when it does.
const VIEWS: [string, () => React.ReactElement, boolean][] = [
  ["the story view", () => <StoryView event={EVENT} />, true],
  ["a story's arc", () => <StoryArc s={STORY} />, false],
  ["a chart row", () => <ChartRow item={ROW} />, true],
  ["the stories list", () => <StoriesPage initial={[STORY as unknown as TrendingStory]} />, true],
];

beforeEach(() => vi.useFakeTimers({ toFake: ["Date"] }));
afterEach(() => vi.useRealTimers());

describe("a cached page is the same bytes whenever it is rendered", () => {
  it.each(VIEWS)("%s", (_, view, hasTimes) => {
    vi.setSystemTime(T0);
    const first = renderToString(view());
    vi.setSystemTime(LATER);
    const second = renderToString(view());
    if (hasTimes) expect(first).toContain("<time");
    expect(second).toBe(first);
  });
});
