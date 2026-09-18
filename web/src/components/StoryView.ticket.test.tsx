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

beforeEach(() => {
  localStorage.clear();
  fetchTrendingStory.mockReset().mockResolvedValue(null);
});

describe("the record — the header", () => {
  it("answers how current and how supported before anything else: updated · subject, then the coverage line", () => {
    render(<StoryView event={event()} />);
    const meta = document.querySelector("header .meta-line")!;
    expect(meta.textContent).toMatch(/Updated/);
    expect(meta.textContent).toMatch(/Business & Markets/);
    // Two reports from one masthead: the coverage line counts outlets AND reports.
    expect(screen.getByText(/1 outlet · 2 reports/)).toBeInTheDocument();
  });

  it("says so when there is one source, in words — never colour alone", () => {
    render(<StoryView event={event({ sources: [src("a1", "2026-09-04T19:55:00Z")] })} />);
    expect(screen.getByText("One source so far")).toBeInTheDocument();
    expect(screen.getByText(/1 outlet · 1 report/)).toBeInTheDocument();
  });

  it("sends the reader back to /feed — never to /, which is the landing for a first visitor", () => {
    render(<StoryView event={event()} />);
    for (const a of [...screen.getAllByRole("link", { name: /back to today/i }), ...screen.getAllByRole("link", { name: /today.s record/i })]) {
      expect(a).toHaveAttribute("href", "/feed");
    }
  });

  it("puts Share on the header (desktop) and in the thumb zone (phone), nowhere else", () => {
    render(<StoryView event={event()} />);
    expect(screen.getAllByRole("button", { name: /share this story/i })).toHaveLength(2);
  });

  it("offers the lenses as one segmented control, with keys announced on desktop", () => {
    render(<StoryView event={event()} />);
    const tabs = screen.getAllByRole("tablist", { name: /read it as/i });
    expect(tabs).toHaveLength(1);
    expect(within(tabs[0]).getByRole("tab", { name: "Reader" })).toHaveAttribute("aria-selected", "true");
  });
});

describe("the record — retired sections (D4) and Why it matters", () => {
  // The route and the passenger list are the perspectives, counted and verbatim.
  // A payload that still carries the LLM cards must not revive them. The
  // impacts, though, are back as "So what": extracted per report, direction
  // as an arrow, horizon in mono.
  it("renders no Perspectives cards; renders the impacts as Why it matters", () => {
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
    expect(screen.getByRole("heading", { name: /Why it matters/ })).toBeInTheDocument();
    expect(screen.getByText("Someone")).toBeInTheDocument();
    expect(screen.getByText("loses")).toBeInTheDocument();
    expect(screen.getByLabelText("negative")).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Perspectives|What to expect/ })).toBeNull();
  });

  it("prints where the reports were filed from, and single origin when the record says so", () => {
    render(<StoryView event={event({ coverage: { origins: { IN: 3 }, unknown: 0, single_origin: true } })} />);
    expect(screen.getByText(/All filed from/)).toBeInTheDocument();
    expect(screen.getByText("Single origin")).toBeInTheDocument();
  });
});

describe("the record — the route", () => {
  const TREE = {
    slug: "s", canonical_slug: "s", label: "L", cast: [], sector: null, source_count: 3, velocity: 0, status: "active",
    boundary_status: "verified" as const,
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
    expect(await screen.findByText("Verified record")).toBeInTheDocument();
    const route = await screen.findByRole("region", { name: /how this story unfolded/i });
    expect(within(route).getByText(/2 DEVELOPMENTS · 0 BRANCHED OFF · 0 ALSO REPORTED · 4 DAYS/)).toBeInTheDocument();
    expect(within(route).getByRole("link", { name: /How it started/ })).toHaveAttribute("href", "/story/e0");
    expect(screen.getByRole("link", { name: "How it unfolded" })).toHaveAttribute("href", "#route");
  });

  it("shows no route section and no Route anchor when the ticket carries no slug", async () => {
    render(<StoryView event={event()} />);
    expect(await screen.findByText("The reader take.")).toBeInTheDocument();
    expect(fetchTrendingStory).not.toHaveBeenCalled();
    expect(screen.queryByRole("region", { name: /how this story unfolded/i })).toBeNull();
    expect(screen.queryByRole("link", { name: /How it unfolded|Related reporting/ })).toBeNull();
  });

  it("prints nothing when the owner has no tree for the story", async () => {
    fetchTrendingStory.mockResolvedValue({ ...TREE, branches: null });
    render(<StoryView event={event({ story_slug: "s" })} />);
    const route = await screen.findByRole("region", { name: /how this story unfolded/i });
    await vi.waitFor(() => expect(within(route).queryByText(/Printing the route/)).toBeNull());
    expect(within(route).queryByLabelText("Storyline structure")).toBeNull();
  });

  it("renders a provisional group as related reporting without a route or chronology", async () => {
    fetchTrendingStory.mockResolvedValue({ ...TREE, boundary_status: "provisional" });
    render(<StoryView event={event({ story_slug: "s" })} />);
    expect(await screen.findByText("Provisional grouping")).toBeInTheDocument();
    const coverage = await screen.findByRole("region", { name: /^related reporting$/i });
    expect(within(coverage).getByText(/not yet verified/i)).toBeInTheDocument();
    expect(within(coverage).queryByLabelText("Storyline structure")).toBeNull();
    expect(screen.getByRole("link", { name: "Related reporting" })).toHaveAttribute("href", "#route");
  });
});

describe("the record — the reports", () => {
  it("prints the first eight reports on the phone and opens the rest on request, the [n] index unchanged; the desktop rail carries them all", async () => {
    const many = Array.from({ length: 12 }, (_, i) => src(`a${i + 1}`, "2026-09-04T19:55:00Z"));
    render(<StoryView event={event({ sources: many })} />);
    const phone = document.querySelector("#sources .lg\\:hidden") as HTMLElement;
    expect(within(phone).getAllByText("A report")).toHaveLength(8);
    const rail = screen.getByRole("complementary", { name: "Evidence" });
    expect(within(rail).getAllByText("A report")).toHaveLength(12);
    const { default: userEvent } = await import("@testing-library/user-event");
    await userEvent.click(screen.getByRole("button", { name: "All 12 reports" }));
    expect(within(phone).getAllByText("A report")).toHaveLength(12);
    expect(within(phone).getByText("[12]")).toBeInTheDocument();
  });

  it("lists what changed newest first, folded past five, each with its outlet and time", async () => {
    const many = Array.from({ length: 7 }, (_, i) => src(`a${i + 1}`, `2026-09-0${(i % 7) + 1}T10:00:00Z`));
    render(<StoryView event={event({ sources: many })} />);
    const changed = screen.getByRole("region", { name: /what changed/i });
    const items = within(changed).getAllByRole("listitem");
    expect(items).toHaveLength(5);
    // a7 is newest (07 Sept) and leads
    expect(within(items[0]).getByText("[7]")).toBeInTheDocument();
    const { default: userEvent } = await import("@testing-library/user-event");
    await userEvent.click(within(changed).getByRole("button", { name: "Show all 7" }));
    expect(within(changed).getAllByRole("listitem")).toHaveLength(7);
  });
});


describe("the record — the section nav reads in page order", () => {
  it("lists The record · What changed · Who said what · Story · Why it matters · Coverage · Ask in the order the sections appear", () => {
    render(<StoryView event={event({
      story_slug: "s",
      claims: [{ speaker: "A", claims: [{ quote_text: "q", quote_start: 0, quote_end: 1, article_id: "a1", source_name: "The Hindu", url: null, published_at: null }] }],
      impacts: [{ id: "i1", entity_name: "Someone", effect: "loses", direction: "negative", horizon: "weeks", confidence: 0.5, parent_impact_id: null }],
    })} />);
    const nav = screen.getByRole("complementary", { name: "On this story" });
    const hrefs = [...nav.querySelectorAll("a")].map((a) => a.getAttribute("href"));
    expect(hrefs).toEqual(["#lens-brief", "#changed", "#said", "#route", "#so-what", "#sources", "#ask"]);
    // and the sections themselves come in that order on the page
    const ids = [...document.querySelectorAll("section[id]")].map((s) => s.id).filter((id) => hrefs.includes(`#${id}`));
    expect(ids).toEqual(["lens-brief", "changed", "said", "route", "so-what", "sources", "ask"]);
  });
});
