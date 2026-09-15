import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import AboutPage from "@/app/about/page";
import type { EventDetail, FeedItem } from "@/lib/api";

const fetchFeed = vi.hoisted(() => vi.fn());
const fetchEvent = vi.hoisted(() => vi.fn());
const fetchTrendingStory = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchFeed, fetchEvent, fetchTrendingStory };
});

const item = (id: string, source_count: number): FeedItem =>
  ({ id, title: `Story ${id}`, source_count, last_updated_at: "2026-09-05T00:00:00Z" }) as FeedItem;

const src = (id: string) => ({ article_id: id, source_name: "Mint", source_slug: "mint", url: "https://m.example/x", title: "A report", published_at: "2026-09-04T19:55:00Z", stance: null, funding: null });

const event = (id: string, over: Partial<EventDetail> = {}): EventDetail =>
  ({
    id, title: `Story ${id}`, summary: null, sector: "finance", subsector: null, image_url: null, regions: [],
    occurred_at: null, last_updated_at: "2026-09-05T00:00:00Z", lens_briefs: {}, lens_points: {}, available_lenses: [],
    coverage: { origins: { IN: 3 }, unknown: 0 }, entities: [], projection: null, sources: [src("a1")],
    perspectives: [], impacts: [], claims: [], ...over,
  }) as unknown as EventDetail;

beforeEach(() => {
  fetchFeed.mockReset();
  fetchEvent.mockReset();
  fetchTrendingStory.mockReset().mockResolvedValue(null);
});
afterEach(() => vi.restoreAllMocks());

describe("/about — three proofs, live", () => {
  it("pulls the passenger list and the coaches from the most-corroborated stories, never inventing them", async () => {
    // The API's order is newest-first; the quoted story is thinner than the lead.
    fetchFeed.mockResolvedValue([item("quoted", 2), item("strong", 9)]);
    fetchEvent.mockImplementation(async (id: string) =>
      id === "quoted"
        ? event("quoted", { claims: [{ speaker: "Anita Dipke", claims: [{ quote_text: "We were receiving proposals", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "https://m.example/x", published_at: null }] }] })
        : event("strong"),
    );
    render(await AboutPage());

    // The passenger list comes from a story that HAS quotes, even if it is not the lead.
    const said = screen.getByRole("heading", { name: "What was said" }).closest("div")!.parentElement!;
    expect(within(said).getByText("“We were receiving proposals”")).toBeInTheDocument();
    expect(within(said).getByRole("link", { name: "Story quoted" })).toHaveAttribute("href", "/story/quoted");
    // The chart's order, not the API's: the nine-outlet story leads the coaches.
    const sources = screen.getByRole("heading", { name: "Sources" }).closest("div")!.parentElement!;
    expect(within(sources).getByRole("link", { name: "Story strong" })).toBeInTheDocument();
    // No slug on either event, so no route and no fetch for one.
    expect(screen.queryByRole("heading", { name: "The route" })).toBeNull();
    expect(fetchTrendingStory).not.toHaveBeenCalled();
  });

  it("renders the route from the owner of the arc when a story carries a tree", async () => {
    fetchFeed.mockResolvedValue([item("e1", 4)]);
    fetchEvent.mockResolvedValue(event("e1", { story_slug: "s" }));
    fetchTrendingStory.mockResolvedValue({
      slug: "s", canonical_slug: "s", label: "L", cast: [], sector: null, source_count: 4, velocity: 0, status: "active", timeline_cast: [],
      developments: [
        { id: "e0", title: "How it started", sector: null, occurred_at: "2026-09-01T00:00:00Z", image_url: null, is_current: false, why: null },
        { id: "e1", title: "Story e1", sector: null, occurred_at: "2026-09-03T00:00:00Z", image_url: null, is_current: false, why: null },
      ],
      branches: { root_id: "e0", nodes: [{ id: "e0", parent_id: null, off_spine: false, depth: 0 }, { id: "e1", parent_id: "e0", off_spine: false, depth: 1 }], shape: { developments: 2, branches: 0, satellites: 0, max_depth: 1 } },
    });
    render(await AboutPage());
    expect(fetchTrendingStory).toHaveBeenCalledWith("s");
    expect(screen.getByRole("heading", { name: "The route" })).toBeInTheDocument();
    expect(screen.getByText(/2 DEVELOPMENTS · 0 BRANCHES · 0 SATELLITES · 3 DAYS/)).toBeInTheDocument();
  });

  it("says the chart is unreachable rather than showing an empty or made-up proof", async () => {
    fetchFeed.mockRejectedValue(new Error("offline"));
    render(await AboutPage());
    expect(screen.getByText(/The chart is unreachable right now/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: /What was said|Sources|The route/ })).toBeNull();
  });

  it("has one action, with one label, and no eyebrow or em-dash anywhere", async () => {
    fetchFeed.mockResolvedValue([]);
    render(await AboutPage());
    const actions = screen.getAllByRole("link", { name: "Read today's chart" });
    expect(actions.length).toBeGreaterThan(0);
    for (const a of actions) expect(a).toHaveAttribute("href", "/");
    expect(document.body.textContent).not.toMatch(/[—–]/);
  });
});
