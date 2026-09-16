import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StoryView } from "@/components/StoryView";
import type { EventDetail } from "@/lib/api";

const fetchTrendingStory = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []), fetchTrendingStory };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [{ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }],
  lensMeta: () => ({ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }),
}));

const src = (id: string, published_at: string | null) => ({
  article_id: id, source_name: "The Hindu", source_slug: "hindu", url: "https://x.test/a", title: "A report", published_at, stance: null, funding: null,
});

function event(over: Partial<EventDetail> = {}): EventDetail {
  return {
    id: "e1",
    title: "A story",
    summary: "A summary.",
    sector: "finance",
    subsector: null,
    image_url: null,
    regions: [],
    occurred_at: "2026-09-04T18:00:00Z",
    last_updated_at: "2026-09-10T00:00:00Z",
    projection: {},
    lens_briefs: { reader: "The reader take." },
    lens_points: {},
    available_lenses: ["reader"],
    coverage: { origins: { IN: 6, US: 2 }, unknown: 0 },
    entities: [],
    sources: [src("a1", "2026-09-04T19:55:00Z"), src("a2", "2026-09-03T10:00:00Z")],
    perspectives: [],
    impacts: [],
    claims: [],
    ...over,
  } as unknown as EventDetail;
}

const mobile = () => within(document.querySelector("article") as HTMLElement);

beforeEach(() => {
  localStorage.clear();
  fetchTrendingStory.mockReset().mockResolvedValue(null);
});

describe("the ticket — the header strip", () => {
  it("prints code · sources · origins · the newest article's IST stamp, on both trees", () => {
    render(<StoryView event={event()} />);
    for (const strip of screen.getAllByLabelText("Story facts")) {
      expect([...strip.querySelectorAll("span")].map((s) => s.textContent)).toEqual([
        "BIZ", "2 sources", "IN ×6 · US ×2", "05 SEPT 2026 01:25 IST",
      ]);
      expect(strip.className).toMatch(/font-mono/);
      expect(strip.parentElement!.className).toMatch(/rule-live/);
    }
  });

  it("sets a single-source story on a dashed rule — state is line form, never hue", () => {
    render(<StoryView event={event({ sources: [src("a1", "2026-09-04T19:55:00Z")] })} />);
    for (const strip of screen.getAllByLabelText("Story facts")) {
      expect(strip.parentElement!.className).toMatch(/rule-single/);
      expect(within(strip).getByText("1 source")).toBeInTheDocument();
    }
  });

  it("sends the reader back to the chart at /feed — never to /, which is the landing for a first visitor", () => {
    render(<StoryView event={event()} />);
    for (const a of screen.getAllByRole("link", { name: /today.s chart/i })) expect(a).toHaveAttribute("href", "/feed");
  });

  it("puts Share on the strip row and in the thumb zone, nowhere else", () => {
    render(<StoryView event={event()} />);
    expect(screen.getAllByRole("button", { name: /share this story/i })).toHaveLength(2);
  });
});

describe("the ticket — retired sections (D4) and So what (founder, 2026-09-17)", () => {
  // The route and the passenger list are the perspectives, counted and verbatim.
  // A payload that still carries the LLM cards must not revive them. The
  // impacts, though, are back as "So what": extracted per report, direction
  // as an arrow, horizon in mono.
  it("renders no Perspectives cards; renders the impacts as So what", () => {
    render(
      <StoryView
        event={event({
          perspectives: [{ label: "Access won", stance: "for", origin_country: "IN", summary: "A model's summary.", article_ids: ["a1"] }],
          impacts: [{ id: "i1", entity_name: "Someone", effect: "loses", direction: "negative", horizon: "weeks", confidence: 0.5, parent_impact_id: null }],
        })}
      />,
    );
    expect(screen.queryByText("Perspectives")).toBeNull();
    expect(screen.queryByText("A model's summary.")).toBeNull();
    expect(screen.queryByText("What to expect")).toBeNull();
    expect(screen.getByText("So what")).toBeInTheDocument();
    expect(screen.getByText("Someone")).toBeInTheDocument();
    expect(screen.getByText("loses")).toBeInTheDocument();
    expect(screen.getByLabelText("negative")).toBeInTheDocument();
    expect(mobile().queryByRole("link", { name: /Perspectives|What to expect/ })).toBeNull();
  });

  it("prints where the reports were filed from, and single origin when the record says so", () => {
    render(<StoryView event={event({ coverage: { origins: { IN: 3 }, unknown: 0, single_origin: true } })} />);
    expect(screen.getByText(/All filed from/)).toBeInTheDocument();
    expect(screen.getByText("Single origin")).toBeInTheDocument();
  });
});

describe("the ticket — the route", () => {
  const TREE = {
    slug: "s", canonical_slug: "s", label: "L", cast: [], sector: null, source_count: 3, velocity: 0, status: "active",
    developments: [
      { id: "e0", title: "How it started", sector: null, occurred_at: "2026-09-01T00:00:00Z", image_url: null, is_current: false, why: null },
      { id: "e1", title: "A story", sector: null, occurred_at: "2026-09-04T00:00:00Z", image_url: null, is_current: false, why: null },
    ],
    timeline_cast: [],
    branches: { root_id: "e0", nodes: [{ id: "e0", parent_id: null, off_spine: false, depth: 0 }, { id: "e1", parent_id: "e0", off_spine: false, depth: 1 }], shape: { developments: 2, branches: 0, satellites: 0, max_depth: 1 } },
  };

  it("asks the owner of the arc — /trending/{slug} — and prints the counted route", async () => {
    fetchTrendingStory.mockResolvedValue(TREE);
    render(<StoryView event={event({ story_slug: "s" })} />);
    expect(fetchTrendingStory).toHaveBeenCalledWith("s");
    const route = await screen.findByRole("region", { name: /how this story unfolded/i });
    expect(within(route).getByText(/2 DEVELOPMENTS · 0 BRANCHED OFF · 0 ALSO REPORTED · 4 DAYS/)).toBeInTheDocument();
    expect(within(route).getByRole("link", { name: /How it started/ })).toHaveAttribute("href", "/story/e0");
    expect(mobile().getByRole("link", { name: "Story" })).toHaveAttribute("href", "#route");
  });

  it("shows no route section and no Route anchor when the ticket carries no slug", async () => {
    render(<StoryView event={event()} />);
    expect(await mobile().findByText("The reader take.")).toBeInTheDocument();
    expect(fetchTrendingStory).not.toHaveBeenCalled();
    expect(screen.queryByRole("region", { name: /how this story unfolded/i })).toBeNull();
    expect(mobile().queryByRole("link", { name: "Story" })).toBeNull();
  });

  it("prints nothing when the owner has no tree for the story", async () => {
    fetchTrendingStory.mockResolvedValue({ ...TREE, branches: null });
    render(<StoryView event={event({ story_slug: "s" })} />);
    const route = await screen.findByRole("region", { name: /how this story unfolded/i });
    await vi.waitFor(() => expect(within(route).queryByText(/Printing the route/)).toBeNull());
    expect(within(route).queryByLabelText("Storyline structure")).toBeNull();
  });
});

describe("the ticket — sources fold", () => {
  it("prints the first eight outlets and opens the rest on request, the [n] index unchanged", async () => {
    const many = Array.from({ length: 12 }, (_, i) => src(`a${i + 1}`, "2026-09-04T19:55:00Z"));
    render(<StoryView event={event({ sources: many })} />);
    expect(screen.getAllByText("A report")).toHaveLength(8);
    const { default: userEvent } = await import("@testing-library/user-event");
    await userEvent.click(screen.getByRole("button", { name: "All 12 sources" }));
    expect(screen.getAllByText("A report")).toHaveLength(12);
    expect(screen.getByText("[12]")).toBeInTheDocument();
  });
});
