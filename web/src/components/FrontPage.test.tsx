import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FrontPage } from "@/components/FrontPage";
import type { FeedItem } from "@/lib/api";

const fetchFeed = vi.hoisted(() => vi.fn());
const fetchTrending = vi.hoisted(() => vi.fn());
const loadProfile = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ fetchFeed, fetchTrending, fetchRegions: () => Promise.resolve([{ code: "IN-KL", name: "Kerala", covered: true }]) }));
vi.mock("@/lib/profile", () => ({ loadProfile }));
const useScrollRestore = vi.hoisted(() => vi.fn());
vi.mock("@/lib/useScrollRestore", () => ({ useScrollRestore }));
// @/lib/scope stays real — the persisted value is the thing under test.

const item = (over: Partial<FeedItem> = {}): FeedItem =>
  ({
    id: "e1",
    title: "A story on the chart",
    headline_lang: "en",
    available_languages: [],
    summary: null,
    sector: "politics",
    subsector: null,
    regions: [],
    image_url: null,
    is_regional: false,
    coverage: null,
    event_type: null,
    source_count: 3,
    cvss_score: null,
    cvss_severity: null,
    kev_listed: false,
    cve_ids: [],
    tickers: [],
    catalyst: null,
    price_impact_direction: null,
    last_updated_at: "2026-09-05T16:05:00Z",
    score: 1,
    ...over,
  }) as FeedItem;

// jsdom's sessionStorage does not route through Storage.prototype, so a spy
// never fires (CLAUDE.md). Stub the global instead.
const session = { store: new Map<string, string>() };
beforeEach(() => {
  fetchFeed.mockReset().mockResolvedValue([item()]);
  fetchTrending.mockReset().mockResolvedValue([]);
  loadProfile.mockReset().mockReturnValue(null);
  localStorage.clear();
  session.store.clear();
  vi.stubGlobal("sessionStorage", {
    getItem: (k: string) => session.store.get(k) ?? null,
    setItem: (k: string, v: string) => void session.store.set(k, v),
    clear: () => session.store.clear(),
  });
});
afterEach(() => vi.unstubAllGlobals());

const lastQuery = () => fetchFeed.mock.calls.at(-1)![0];

describe("FrontPage — one chart for everyone (D2)", () => {
  it("TODAY sends no interests, even for a reader who has them", async () => {
    loadProfile.mockReturnValue({ state: "IN-KA", interests: ["sports"], languages: ["en"] });
    render(<FrontPage />);
    await waitFor(() => expect(fetchFeed).toHaveBeenCalled());
    expect(lastQuery().interests).toBeUndefined();
    expect(lastQuery().sector).toBeUndefined();
  });

  it("offers FOR YOU only once the reader has picked interests, and only that tab sends them", async () => {
    render(<FrontPage />);
    await screen.findAllByText("A story on the chart");
    expect(screen.queryByRole("tab", { name: "For you" })).toBeNull();

    loadProfile.mockReturnValue({ state: "IN-KA", interests: ["sports"], languages: ["en"] });
    render(<FrontPage />);
    await userEvent.click(await screen.findByRole("tab", { name: "For you" }));
    await waitFor(() => expect(lastQuery().interests).toEqual(["sports"]));
  });

  it("asks the API for the whole group when a sector is chosen — BIZ is business AND finance", async () => {
    render(<FrontPage sector="business" />);
    await waitFor(() => expect(fetchFeed).toHaveBeenCalled());
    expect(lastQuery().sector).toBe("business,finance");
    expect(screen.getByRole("link", { name: /BIZ/ })).toHaveAttribute("aria-current", "page");
  });

  it("resolves a legacy pipeline slug to its group", async () => {
    render(<FrontPage sector="finance" />);
    await waitFor(() => expect(fetchFeed).toHaveBeenCalled());
    expect(lastQuery().sector).toBe("business,finance");
  });

  it("names the subject when a sector has nothing today", async () => {
    fetchFeed.mockResolvedValue([]);
    render(<FrontPage sector="sports" />);
    expect(await screen.findByText(/No Sports records today/)).toBeInTheDocument();
  });
});

describe("FrontPage — scope", () => {
  // REGRESSION (carried from the old feed): scope was per-page state re-seeded
  // from the profile on every mount, so picking All and reloading snapped
  // straight back to your state.
  it("keeps the All the reader picked instead of snapping back to their state", async () => {
    localStorage.setItem("parse.scope.v2", "all");
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<FrontPage />);
    expect(await screen.findByRole("button", { name: "All" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: /Your state|Kerala/ })).toHaveAttribute("aria-pressed", "false");
  });

  // REGRESSION (ISSUE-001): a saved region scope can outlive the state it named.
  it("offers no state pill to a reader with no state, and forgets a saved state scope", async () => {
    localStorage.setItem("parse.scope.v2", "region");
    render(<FrontPage />);
    await screen.findAllByText("A story on the chart");
    expect(screen.queryByRole("button", { name: /Your state/ })).toBeNull();
    // National and World are absolute slices; everyone gets them.
    expect(screen.getByRole("button", { name: "National" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "World" })).toBeInTheDocument();
    expect(lastQuery().scope).toBe("all");
  });

  it("World is what does not involve India, for any reader", async () => {
    render(<FrontPage />);
    await screen.findAllByText("A story on the chart");
    await userEvent.click(screen.getByRole("button", { name: "World" }));
    await waitFor(() => expect(lastQuery().scope).toBe("world"));
  });

  it("persists the pick so it survives a reload and carries to Trending", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<FrontPage />);
    await userEvent.click(await screen.findByRole("button", { name: "National" }));
    expect(localStorage.getItem("parse.scope.v2")).toBe("national");
  });

  // REGRESSION: the three pills filtered ONE state-first page in the browser. A
  // Karnataka reader (more than a page of Karnataka news) saw "National" empty
  // and "All" identical to "Your state". Each pill is now its own server slice.
  it("asks the API for each slice instead of filtering one page", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<FrontPage />);
    await screen.findAllByText("A story on the chart");
    expect(lastQuery().scope).toBe("all");
    await userEvent.click(screen.getByRole("button", { name: /Your state|Kerala/ }));
    await waitFor(() => expect(lastQuery().scope).toBe("region"));
    await userEvent.click(screen.getByRole("button", { name: "National" }));
    await waitFor(() => expect(lastQuery().scope).toBe("national"));
    expect(fetchFeed).toHaveBeenCalledTimes(3);
  });

  it("names the reader's state on the pill once the regions have loaded", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<FrontPage />);
    expect(await screen.findByRole("button", { name: "Kerala" })).toBeInTheDocument();
  });
});

// Pages v3 · Today: the phone leads with a rail of the day's multi-outlet
// stories — on All + Today only, never a single-source story.
describe("FrontPage — top of the record", () => {
  it("rails the multi-outlet stories on All, most-reported first, and leaves single-source ones to the list", async () => {
    fetchFeed.mockResolvedValue([item({ id: "a", title: "Two outlets", source_count: 2 }), item({ id: "b", title: "Nine outlets", source_count: 9 }), item({ id: "c", title: "One outlet", source_count: 1 })]);
    render(<FrontPage />);
    const rail = (await screen.findByRole("heading", { name: "Top of the record" })).closest("section")!;
    expect(within(rail).getAllByRole("heading", { level: 3 }).map((h) => h.textContent)).toEqual(["Nine outlets", "Two outlets"]);
    expect(within(rail).getByText("1 / 2")).toBeInTheDocument();
  });

  it("is not on a subject page", async () => {
    render(<FrontPage sector="politics" />);
    await screen.findAllByText("A story on the chart");
    expect(screen.queryByRole("heading", { name: "Top of the record" })).toBeNull();
  });
});

describe("FrontPage — mount fetches", () => {
  // REGRESSION: loadProfile() is a synchronous localStorage read but runs in a
  // mount effect, so every fetch effect fired once with profile=null and again
  // with the profile — discarded round trips on a page that re-mounts every
  // time the reader returns from a story.
  it("never fetches before the profile has loaded", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL", languages: ["kn", "en"] });
    render(<FrontPage />);
    await waitFor(() => expect(fetchFeed).toHaveBeenCalled());
    for (const [query] of fetchFeed.mock.calls) {
      expect(query.state).toBe("IN-KL");
      expect(query.languages).toEqual(["kn", "en"]);
    }
  });

  it("says what failed on the chart itself, never a blank list", async () => {
    fetchFeed.mockRejectedValue(new Error("offline"));
    render(<FrontPage />);
    expect(await screen.findByText(/API is unreachable/)).toBeInTheDocument();
    expect(screen.queryByRole("list")).toBeNull();
  });
});

describe("FrontPage — marks the reader as returning", () => {
  // `/` reads this cookie server-side to skip the landing. jsdom implements
  // document.cookie, so assert the real thing rather than a spy.
  it("sets the prism.returning cookie on mount", async () => {
    document.cookie = "prism.returning=; path=/; max-age=0";
    render(<FrontPage />);
    await screen.findByRole("list");
    expect(document.cookie).toContain("prism.returning=1");
  });
});

describe("the masthead says when the record went quiet", () => {
  it("prints 'quiet since' once no report has arrived for twelve hours", async () => {
    const old = new Date(Date.now() - 20 * 3_600_000).toISOString();
    fetchFeed.mockResolvedValue([item({ latest_published_at: old, last_updated_at: old })]);
    render(<FrontPage />);
    expect(await screen.findByText(/quiet since/i)).toBeInTheDocument();
  });
});

// REGRESSION (founder, 2026-09-20): back from a story landed at the top of the
// chart. The chart restores its scroll once its list is present, keyed by the
// slice so one scope's offset never lands on another's.
describe("FrontPage — coming back", () => {
  it("restores scroll for the slice on screen, only once the list has loaded", async () => {
    useScrollRestore.mockClear();
    loadProfile.mockReturnValue({ state: "IN-KA", interests: [], languages: ["en"] });
    fetchFeed.mockResolvedValue([item()]);
    render(<FrontPage />);
    // Before the list: not ready.
    expect(useScrollRestore.mock.calls[0][1]).toBe(false);
    await waitFor(() => expect(useScrollRestore).toHaveBeenLastCalledWith(expect.stringMatching(/^feed:all:today:(all|region):scrollY$/), true));
  });
});
