import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { StoriesPage as TrendingPage } from "@/components/StoriesPage";
import type { TrendingStory } from "@/lib/api";

const fetchTrending = vi.hoisted(() => vi.fn());
const fetchRegions = vi.hoisted(() => vi.fn());
const loadProfile = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ fetchTrending, fetchRegions }));
vi.mock("@/lib/profile", () => ({ loadProfile }));
// @/lib/scope is deliberately NOT mocked: the persisted value is the point.

const DAY = 86_400_000;
const now = Date.now();
const iso = (msAgo: number) => new Date(now - msAgo).toISOString();

function story(over: Partial<TrendingStory> = {}): TrendingStory {
  return {
    slug: "kerala-power", label: "CPI(M) · Pinarayi Vijayan", cast: ["CPI(M)", "Pinarayi Vijayan"],
    source_count: 4, velocity: 3, developments: 5, sector: "politics",
    hero_title: "Kerala power crisis deepens", hero_image: null, route: null, photos: [],
    hero_event_id: "ev-1", first_seen_at: iso(6 * DAY), last_updated_at: iso(2 * 3_600_000),
    ...over,
  };
}

const lastQuery = () => fetchTrending.mock.calls.at(-1)![0];
const row = (name: string | RegExp) => screen.getByRole("link", { name });

beforeEach(() => {
  fetchRegions.mockReset().mockResolvedValue([{ code: "IN-KL", name: "Kerala" }, { code: "IN-BR", name: "Bihar" }]);
  fetchTrending.mockReset().mockResolvedValue([story()]);
  loadProfile.mockReset().mockReturnValue(null);
  localStorage.clear();
});

describe("Trending — scope", () => {
  it("offers no scope control and asks nationally when the reader has no state", async () => {
    render(<TrendingPage />);
    await screen.findByRole("list");
    expect(screen.queryByRole("button", { name: "National" })).toBeNull();
    expect(lastQuery()).toMatchObject({ state: null });
  });

  it("opens on the reader's own state, named from /regions, when they have one", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);
    expect(await screen.findByRole("button", { name: "Kerala" })).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => expect(lastQuery()).toMatchObject({ state: "IN-KL" }));
  });

  it("shows the code until a name arrives, and keeps it when none does", async () => {
    loadProfile.mockReturnValue({ state: "IN-GJ" });
    render(<TrendingPage />);
    expect(await screen.findByRole("button", { name: "IN-GJ" })).toBeInTheDocument();
  });

  it("switches to National and persists the pick for the Feed", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);
    await userEvent.click(await screen.findByRole("button", { name: "National" }));
    await waitFor(() => expect(lastQuery()).toMatchObject({ state: null }));
    expect(localStorage.getItem("parse.scope.v2")).toBe("national");
  });

  // REGRESSION: Trending has no "all" tier. A Feed-saved "all" opens here as
  // National, and tapping National must NOT narrow the Feed's "all" to "national".
  it("reads a Feed-saved 'all' as National without overwriting it", async () => {
    localStorage.setItem("parse.scope.v2", "all");
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<TrendingPage />);
    expect(await screen.findByRole("button", { name: "National" })).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(screen.getByRole("button", { name: "National" }));
    expect(localStorage.getItem("parse.scope.v2")).toBe("all");
  });
});

describe("Trending — the sector strip", () => {
  it("asks for the whole group, comma-separated, and ALL clears it", async () => {
    render(<TrendingPage />);
    await screen.findByRole("list");
    await userEvent.click(screen.getByRole("button", { name: /Business & Markets/ }));
    await waitFor(() => expect(lastQuery()).toMatchObject({ sector: "business,finance" }));
    await userEvent.click(screen.getByRole("button", { name: /All stories/ }));
    await waitFor(() => expect(lastQuery()).toMatchObject({ sector: null }));
  });
});

describe("Trending — the chart of arcs", () => {
  // The Reading board's ArcRow: status first, subject · span · last update,
  // the name, and the one-ink bar labelled "k developments · n outlets".
  it("says a provisional boundary is a provisional grouping and opens its honest group page", async () => {
    render(<TrendingPage />);
    const r = await screen.findByRole("link", { name: /CPI\(M\) · Pinarayi Vijayan/ });
    expect(r).toHaveAttribute("href", "/trending/kerala-power");
    expect(r.textContent).toMatch(/5 developments · 4 outlets/);
    expect(r.textContent).toMatch(/5 days/); // 6 days less two hours, floored
    expect(r.textContent).toMatch(/updated 2h ago/);
    expect(r.textContent).toMatch(/Provisional grouping/);
    expect(r.textContent).not.toMatch(/Verified/);
  });

  it("shows a route and opens its hero only after the boundary is verified", async () => {
    fetchTrending.mockResolvedValue([story({ boundary_status: "verified" })]);
    render(<TrendingPage />);
    const r = await screen.findByRole("link", { name: /CPI\(M\) · Pinarayi Vijayan/ });
    expect(r).toHaveAttribute("href", "/story/ev-1#route");
    expect(r.textContent).toMatch(/5 developments/);
    expect(r.textContent).toMatch(/Verified/);
  });

  it("opens the arc page when a story has no hero event, and falls back to the hero headline without a label", async () => {
    fetchTrending.mockResolvedValue([story({ hero_event_id: null, label: null as unknown as string })]);
    render(<TrendingPage />);
    expect(await screen.findByRole("link", { name: /Kerala power crisis deepens/ })).toHaveAttribute("href", "/trending/kerala-power");
  });

  // State is line form: dashed for a single outlet, half-weight when the arc has not moved in three days.
  it("prints a single-outlet story on a dashed card and a stale one at reduced weight", async () => {
    fetchTrending.mockResolvedValue([
      story({ slug: "one", label: "One outlet", source_count: 1 }),
      story({ slug: "old", label: "Old arc", last_updated_at: iso(5 * DAY), velocity: 0 }),
      story({ slug: "live", label: "Live arc" }),
    ]);
    render(<TrendingPage />);
    await screen.findByRole("list");
    expect(row(/One outlet/).className).toContain("single");
    expect(row(/Old arc/).className).toContain("p-row--stale");
    expect(row(/Live arc/).className).not.toContain("single");
    expect(row(/Live arc/).className).not.toContain("p-row--stale");
  });

  it("says so when nothing is moving, and when the API is down", async () => {
    fetchTrending.mockResolvedValue([]);
    const { unmount } = render(<TrendingPage />);
    expect(await screen.findByText("No developing stories right now")).toBeInTheDocument();
    unmount();
    fetchTrending.mockRejectedValue(new Error("down"));
    render(<TrendingPage />);
    expect(await screen.findByText(/unreachable/)).toBeInTheDocument();
  });
});

// The Reading board draws no photographs on the Stories list: a row is its
// status, its counts and its name.
describe("Stories — no photographs on the list", () => {
  it("draws no photograph even when the story has some", async () => {
    const outlet = { slug: "thehindu", publisher: "thehindu", name: "The Hindu", code: "TH", origin: "national", language: "en", domain: "thehindu.com" };
    fetchTrending.mockResolvedValue([story({ photos: [{ url: "https://x/0.jpg", article_url: null, outlet }] })]);
    render(<TrendingPage />);
    await screen.findAllByText(/CPI\(M\)/);
    expect(screen.queryByRole("img")).toBeNull();
    expect(screen.queryByRole("figure")).toBeNull();
  });
});

describe("Stories — an empty subject", () => {
  it("names the subject and offers every subject back", async () => {
    render(<TrendingPage />);
    await screen.findByRole("list");
    fetchTrending.mockResolvedValue([]);
    await userEvent.click(screen.getByRole("button", { name: /Sports/ }));
    expect(await screen.findByText("No developing Sports stories right now")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "All subjects →" }));
    await waitFor(() => expect(lastQuery()).toMatchObject({ sector: null }));
  });
});

describe("Stories — the counted line is honest about the capped page", () => {
  // The API serves a ranked page of 24. Ranked by new reporting, the moving ones
  // come first, so a full page of them may hide more: "24+", like the total.
  it("prints a full page of moving stories as 24+, not 24", async () => {
    fetchTrending.mockResolvedValue(Array.from({ length: 24 }, (_, i) => story({ slug: `s-${i}`, hero_event_id: `e-${i}`, velocity: 2 })));
    render(<TrendingPage />);
    expect(await screen.findByText(/24\+ developing stories · 24\+ moving now/)).toBeInTheDocument();
  });

  it("prints fewer moving stories exactly", async () => {
    fetchTrending.mockResolvedValue([story({ slug: "a", hero_event_id: "a", velocity: 2 }), story({ slug: "b", hero_event_id: "b", velocity: 0 })]);
    render(<TrendingPage />);
    expect(await screen.findByText(/2 developing stories · 1 moving now/)).toBeInTheDocument();
  });
});
