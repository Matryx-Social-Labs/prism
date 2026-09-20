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
    await userEvent.click(screen.getByRole("button", { name: /BIZ/ }));
    await waitFor(() => expect(lastQuery()).toMatchObject({ sector: "business,finance" }));
    await userEvent.click(screen.getByRole("button", { name: /ALL/ }));
    await waitFor(() => expect(lastQuery()).toMatchObject({ sector: null }));
  });
});

describe("Trending — the chart of arcs", () => {
  it("fails a provisional boundary closed to related events and opens its honest group page", async () => {
    render(<TrendingPage />);
    const r = await screen.findByRole("link", { name: /CPI\(M\) · Pinarayi Vijayan/ });
    expect(r).toHaveAttribute("href", "/trending/kerala-power");
    expect(r.textContent).toMatch(/5 related reports/);
    expect(r.textContent).toMatch(/4 outlets/);
    expect(r.textContent).toMatch(/5 days/); // 6 days less two hours, floored
    expect(r.textContent).toMatch(/moving now/);
    expect(r.textContent).toMatch(/Grouping under review/);
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
    expect(row(/Old arc/).style.opacity).toBe("0.75");
    expect(row(/Live arc/).className).not.toContain("single");
    expect(row(/Live arc/).style.opacity).toBe("");
  });

  it("says so when nothing is moving, and when the API is down", async () => {
    fetchTrending.mockResolvedValue([]);
    const { unmount } = render(<TrendingPage />);
    expect(await screen.findByText(/No story is developing in all sectors/)).toBeInTheDocument();
    unmount();
    fetchTrending.mockRejectedValue(new Error("down"));
    render(<TrendingPage />);
    expect(await screen.findByText(/unreachable/)).toBeInTheDocument();
  });
});

// The story's picture is many pictures (founder, 2026-09-21): up to three of
// the developments' photographs, credited, fanned on the row; a "+N" counts
// the rest; nothing when there are none.
describe("Stories — the photo pile", () => {
  const outlet = { slug: "thehindu", publisher: "thehindu", name: "The Hindu", code: "TH", origin: "national", language: "en", domain: "thehindu.com" };
  const pics = (n: number) => Array.from({ length: n }, (_, i) => ({ url: `https://x/${i}.jpg`, article_url: `https://h/${i}`, outlet }));

  it("shows at most three photographs, the front one credited, and counts the rest", async () => {
    fetchTrending.mockResolvedValue([story({ photos: pics(4) })]);
    render(<TrendingPage />);
    const pile = await screen.findByRole("figure", { name: "4 photographs from the reports" });
    // Three photographs (the fourth image is the outlet's favicon on the front card).
    expect(pile.querySelectorAll('img[alt^="Photo:"]')).toHaveLength(3);
    expect(pile.querySelector('img[alt^="Photo:"]')).toHaveAttribute("alt", "Photo: The Hindu");
    expect(pile).toHaveTextContent("+1");
  });

  it("a story without photographs has no pile", async () => {
    fetchTrending.mockResolvedValue([story({ photos: [] })]);
    render(<TrendingPage />);
    await screen.findAllByText(/CPI\(M\)/);
    expect(screen.queryByRole("figure")).toBeNull();
  });
});
