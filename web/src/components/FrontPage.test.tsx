import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { FrontPage } from "@/components/FrontPage";
import type { FeedItem } from "@/lib/api";

const fetchFeed = vi.hoisted(() => vi.fn());
const loadProfile = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ fetchFeed }));
vi.mock("@/lib/profile", () => ({ loadProfile }));
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
    await screen.findByText("A story on the chart");
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
    expect(await screen.findByText(/No Sports stories on today's chart/)).toBeInTheDocument();
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
    expect(screen.getByRole("button", { name: "Your state" })).toHaveAttribute("aria-pressed", "false");
  });

  // REGRESSION (ISSUE-001): a saved region scope can outlive the state it named.
  it("offers no scope control at all to a reader with no state", async () => {
    localStorage.setItem("parse.scope.v2", "region");
    render(<FrontPage />);
    await screen.findByText("A story on the chart");
    expect(screen.queryByRole("button", { name: "Your state" })).toBeNull();
  });

  it("persists the pick so it survives a reload and carries to Trending", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<FrontPage />);
    await userEvent.click(await screen.findByRole("button", { name: "National" }));
    expect(localStorage.getItem("parse.scope.v2")).toBe("national");
  });

  it("filters the rows the API already tagged, so ALL is the same for every reader", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    fetchFeed.mockResolvedValue([item({ id: "r", title: "Regional", is_regional: true }), item({ id: "n", title: "National story", is_regional: false })]);
    render(<FrontPage />);
    await screen.findByText("Regional");
    await userEvent.click(screen.getByRole("button", { name: "Your state" }));
    expect(screen.queryByText("National story")).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "All" }));
    expect(screen.getByText("National story")).toBeInTheDocument();
    // The API was asked once; scope never refetches.
    expect(fetchFeed).toHaveBeenCalledTimes(1);
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

describe("FrontPage — the promise line", () => {
  it("shows the promise to a signed-out first visitor once per session", async () => {
    render(<FrontPage />);
    expect(await screen.findByText(/One story\. Every perspective\./)).toBeInTheDocument();
    render(<FrontPage />);
    await waitFor(() => expect(screen.getAllByText("A story on the chart")).toHaveLength(2));
    expect(screen.getAllByText(/One story\. Every perspective\./)).toHaveLength(1);
  });

  it("never shows it to a reader with a profile, nor on a sector page", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<FrontPage />);
    await screen.findByText("A story on the chart");
    expect(screen.queryByText(/One story\. Every perspective\./)).toBeNull();

    loadProfile.mockReturnValue(null);
    render(<FrontPage sector="politics" />);
    await waitFor(() => expect(fetchFeed).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(/One story\. Every perspective\./)).toBeNull();
  });
});
