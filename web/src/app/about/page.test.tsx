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

describe("/about — the product as the proof, live", () => {
  it("leads with the most-corroborated general story and quotes from the story that has a verified quote", async () => {
    // The API's order is newest-first; the quoted story is thinner than the lead.
    fetchFeed.mockResolvedValue([item("quoted", 2), item("strong", 9)]);
    fetchEvent.mockImplementation(async (id: string) =>
      id === "quoted"
        ? event("quoted", { claims: [{ speaker: "Anita Dipke", claims: [{ quote_text: "We were receiving proposals", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "https://m.example/x", published_at: null }] }] })
        : event("strong", { sources: [src("a1"), src("a2")] }),
    );
    render(await AboutPage());

    // The chart rows: the nine-outlet story leads, by the chart's order, not the API's.
    const rows = screen.getByRole("heading", { name: "Today's chart" }).parentElement!.parentElement!;
    const links = within(rows).getAllByRole("link", { name: /Story/ });
    expect(links[0]).toHaveAttribute("href", "/story/strong");
    // The count cell shows the feature in the row's own grammar: a real row with its count.
    const count = screen.getByRole("heading", { name: "One story, not fifty headlines" }).parentElement!;
    expect(within(count).getByRole("link", { name: /Story quoted/ })).toHaveAttribute("href", "/story/quoted");
    expect(within(count).getByLabelText("2 sources")).toBeInTheDocument();
    // The quote cell comes from a story that HAS quotes, even if it is not the lead.
    const said = screen.getByRole("heading", { name: "Who said what, in their own words" }).parentElement!;
    expect(within(said).getByText("“We were receiving proposals”")).toBeInTheDocument();
    // No slug on either event, so no route cell and no fetch for one.
    expect(screen.queryByRole("heading", { name: "Follow the story as it moves" })).toBeNull();
    expect(fetchTrendingStory).not.toHaveBeenCalled();
  });

  it("keeps the cyber record off the landing: a general reader meets general news first", async () => {
    fetchFeed.mockResolvedValue([item("cve", 40), item("poll", 5)].map((i, n) => ({ ...i, sector: n === 0 ? "cybersecurity" : "politics" })));
    fetchEvent.mockImplementation(async (id: string) => event(id));
    render(await AboutPage());
    expect(screen.queryByRole("link", { name: /Story cve/ })).toBeNull();
    expect(screen.getAllByRole("link", { name: /Story poll/ }).length).toBeGreaterThan(0);
  });

  it("renders the route from the owner of the arc when a story carries a tree", async () => {
    fetchFeed.mockResolvedValue([item("e1", 4)]);
    fetchEvent.mockResolvedValue(event("e1", { story_slug: "s" }));
    fetchTrendingStory.mockResolvedValue({
      slug: "s", canonical_slug: "s", label: "L", cast: [], sector: null, source_count: 4, velocity: 0, status: "active", timeline_cast: [], boundary_status: "verified",
      developments: [
        { id: "e0", title: "How it started", sector: null, occurred_at: "2026-09-01T00:00:00Z", image_url: null, is_current: false, why: null },
        { id: "e1", title: "Story e1", sector: null, occurred_at: "2026-09-03T00:00:00Z", image_url: null, is_current: false, why: null },
        { id: "e2", title: "What followed", sector: null, occurred_at: "2026-09-04T00:00:00Z", image_url: null, is_current: false, why: null },
      ],
      // Three on the spine: a route with fewer shows no route, so the landing skips it.
      branches: { root_id: "e0", nodes: [{ id: "e0", parent_id: null, off_spine: false, depth: 0 }, { id: "e1", parent_id: "e0", off_spine: false, depth: 1 }, { id: "e2", parent_id: "e1", off_spine: false, depth: 2 }], shape: { developments: 3, branches: 0, satellites: 0, max_depth: 2 } },
    });
    render(await AboutPage());
    expect(fetchTrendingStory).toHaveBeenCalledWith("s");
    expect(screen.getByRole("heading", { name: "Follow the story as it moves" })).toBeInTheDocument();
    expect(screen.getByText(/3 DEVELOPMENTS · 0 BRANCHED OFF · 0 ALSO REPORTED · 4 DAYS/)).toBeInTheDocument();
  });

  it("skips the route when a story has fewer than three developments on the spine", async () => {
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
    expect(screen.queryByRole("heading", { name: "Follow the story as it moves" })).toBeNull();
  });

  it("says the chart is unreachable rather than showing an empty or made-up proof", async () => {
    fetchFeed.mockRejectedValue(new Error("offline"));
    render(await AboutPage());
    expect(screen.getAllByText(/The chart is unreachable right now/).length).toBeGreaterThan(0);
    expect(screen.queryByRole("heading", { name: "Follow the story as it moves" })).toBeNull();
  });

  it("has one action, with one label, and no eyebrow or em-dash anywhere", async () => {
    fetchFeed.mockResolvedValue([]);
    render(await AboutPage());
    const actions = screen.getAllByRole("link", { name: "Read today's chart" });
    expect(actions.length).toBeGreaterThan(0);
    // /feed, never /: under the revised D5 a first visitor at / gets this page again.
    for (const a of actions) expect(a).toHaveAttribute("href", "/feed");
    expect(document.body.textContent).not.toMatch(/[—–]/);
  });
});
