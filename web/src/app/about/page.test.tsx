import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import AboutPage from "@/app/about/page";
import type { EventDetail, FeedItem } from "@/lib/api";

const fetchFeed = vi.hoisted(() => vi.fn());
const fetchEvent = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchFeed, fetchEvent };
});

const item = (id: string, source_count: number, sector = "politics"): FeedItem =>
  ({ id, title: `Story ${id}`, source_count, sector, last_updated_at: "2026-09-05T00:00:00Z", regions: [], is_regional: false }) as unknown as FeedItem;

const src = (id: string, name = "Mint") => ({
  article_id: id, source_name: name, source_slug: name.toLowerCase(), url: `https://m.example/${id}`, title: `Report ${id}`, published_at: "2026-09-04T19:55:00Z",
  stance: null, funding: null, code: name.slice(0, 2).toUpperCase(), origin: "national", language: "en", publisher: name, domain: null, image_url: null,
});

const event = (id: string, over: Partial<EventDetail> = {}): EventDetail =>
  ({
    id, title: `Story ${id}`, summary: null, sector: "politics", subsector: null, image_url: null, regions: [],
    occurred_at: null, last_updated_at: "2026-09-05T00:00:00Z", lens_briefs: {}, lens_points: {}, available_lenses: [],
    coverage: null, entities: [], projection: null, sources: [src("a1")], perspectives: [], impacts: [], claims: [], ...over,
  }) as unknown as EventDetail;

const quoted = () =>
  event("rich", {
    sources: [src("a1", "Mint"), src("a2", "The Hindu"), src("a3", "Reuters")],
    lens_briefs: { reader: "The council voted to widen the road. Traders said they were not consulted. The decision matters because it reopens a 2019 plan." },
    lens_points: { reader: ["Whether the plan is notified"] },
    claims: [{ speaker: "Anita Dipke", role: "Karnataka Urban Development Minister", claims: [{ quote_text: "We were receiving proposals from every ward", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "https://m.example/a1", published_at: null }] }],
  });

beforeEach(() => {
  fetchFeed.mockReset();
  fetchEvent.mockReset();
});
afterEach(() => vi.restoreAllMocks());

describe("/about — how Prism works, on one live story", () => {
  it("follows the story that shows the most: many reports, a quote with a role, a brief", async () => {
    fetchFeed.mockResolvedValue([item("thin", 1), item("rich", 3), item("wide", 5)]);
    fetchEvent.mockImplementation(async (id: string) => (id === "rich" ? quoted() : event(id, { sources: id === "wide" ? [src("w1"), src("w2"), src("w3"), src("w4"), src("w5")] : [src("t1")] })));
    render(await AboutPage());

    // The example card names the story and links to it: a quote with a role outranks five bare reports.
    expect(screen.getByRole("link", { name: "Story rich" })).toHaveAttribute("href", "/story/rich");
    // Step 01: the reports as they arrived, oldest first, one card each.
    const reports = screen.getByRole("list", { name: "The reports, oldest first" });
    expect(within(reports).getAllByRole("link")).toHaveLength(3);
    // Step 04: the quote, verbatim, with who the speaker is.
    expect(screen.getByText("“We were receiving proposals from every ward”")).toBeInTheDocument();
    expect(screen.getAllByText("Karnataka Urban Development Minister").length).toBeGreaterThan(0);
    // Step 05: the brief as points, the why-it-matters line among them.
    expect(screen.getByText(/reopens a 2019 plan/)).toBeInTheDocument();
    expect(screen.getByText(/What to watch: Whether the plan is notified/)).toBeInTheDocument();
    // Eight steps, in order, in the rail.
    const rail = screen.getByRole("navigation", { name: "Steps" });
    expect(within(rail).getAllByRole("link").map((a) => a.textContent?.replace(/^\d+/, ""))).toEqual([
      "Reports come in", "One record", "Who covered it", "Who said what", "The brief", "Read it through a lens", "Ask the record", "What Prism refuses",
    ]);
  });

  it("keeps the cyber record out of the example", async () => {
    fetchFeed.mockResolvedValue([item("cve", 40, "cybersecurity"), item("poll", 2)]);
    fetchEvent.mockImplementation(async (id: string) => event(id));
    render(await AboutPage());
    expect(screen.queryByRole("link", { name: /Story cve/ })).toBeNull();
    expect(screen.getByRole("link", { name: "Story poll" })).toBeInTheDocument();
  });

  it("still explains every step when the record is unreachable, and says so", async () => {
    fetchFeed.mockRejectedValue(new Error("offline"));
    render(await AboutPage());
    expect(screen.getByText(/The live record is unavailable right now/)).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 2 }).length).toBeGreaterThanOrEqual(8);
    expect(screen.getAllByText(/is not available in the current window/).length).toBeGreaterThan(0);
  });

  it("names what Prism refuses to do, and uses no em-dash anywhere", async () => {
    fetchFeed.mockResolvedValue([]);
    render(await AboutPage());
    for (const head of ["No invented numbers.", "No unsourced lines.", "No left, right or centre.", "No photos of its own.", "No silent edits."]) {
      expect(screen.getByText(head)).toBeInTheDocument();
    }
    expect(document.body.textContent).not.toMatch(/[—–]/);
  });
});
