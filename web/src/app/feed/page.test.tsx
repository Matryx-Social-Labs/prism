import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import FeedPage from "@/app/feed/page";

const fetchFeed = vi.hoisted(() => vi.fn());
const fetchDigest = vi.hoisted(() => vi.fn());
const fetchTrending = vi.hoisted(() => vi.fn());
const fetchRegions = vi.hoisted(() => vi.fn());
const loadProfile = vi.hoisted(() => vi.fn());
const useSession = vi.hoisted(() => vi.fn());
const watchlistEvents = vi.hoisted(() => vi.fn());
const useTaxonomy = vi.hoisted(() => vi.fn());

vi.mock("@/lib/api", () => ({ fetchFeed, fetchDigest, fetchTrending, fetchRegions }));
vi.mock("@/lib/profile", () => ({ loadProfile }));
vi.mock("@/lib/session", () => ({ useSession }));
vi.mock("@/lib/watchlist", () => ({ watchlistEvents }));
vi.mock("@/components/ProfileEditor", () => ({ useTaxonomy }));
// @/lib/scope stays real — the persisted value is the thing under test.

beforeEach(() => {
  // Rejecting keeps `items` null, so the module-level feed cache is never
  // written and one test's scope can't seed the next one's initial state.
  fetchFeed.mockReset().mockRejectedValue(new Error("offline"));
  fetchDigest.mockReset().mockResolvedValue(null);
  fetchTrending.mockReset().mockResolvedValue([]);
  fetchRegions.mockReset().mockResolvedValue([{ code: "IN-KL", name: "Kerala" }]);
  loadProfile.mockReset().mockReturnValue(null);
  useSession.mockReset().mockReturnValue(null);
  watchlistEvents.mockReset().mockResolvedValue([]);
  useTaxonomy.mockReset().mockReturnValue([{ slug: "politics", name: "Politics", subsectors: [] }]);
  localStorage.clear();
});

describe("Feed — scope", () => {
  // REGRESSION: scope was per-page state re-seeded from the profile on every
  // mount, so picking World and reloading snapped straight back to your state.
  it("keeps the World the reader picked instead of snapping back to their state", async () => {
    localStorage.setItem("parse.scope.v1", "all");
    loadProfile.mockReturnValue({ state: "IN-KL" });

    render(<FeedPage />);

    expect(await screen.findByRole("button", { name: /World/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Kerala/ })).not.toBeInTheDocument();
  });

  // REGRESSION (ISSUE-001): scope and profile are separate localStorage keys, so
  // they drift — pick "Your state", later clear the state, and the saved region
  // scope outlived the thing it named. The chip then read "Your state" over an
  // unfiltered feed, and the sheet's own option was disabled so the reader was
  // stuck with a label that lied.
  it("does not claim Your state when the reader has no state", async () => {
    localStorage.setItem("parse.scope.v1", "region");

    render(<FeedPage />);

    expect(await screen.findByRole("button", { name: /World/ })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Your state/ })).not.toBeInTheDocument();
  });

  it("still opens on the reader's state when they have never chosen", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });

    render(<FeedPage />);

    expect(await screen.findByRole("button", { name: /Kerala/ })).toBeInTheDocument();
  });

  it("persists the pick so it survives the reload and carries to Trending", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<FeedPage />);

    await userEvent.click(await screen.findByRole("button", { name: /Kerala/ }));
    await userEvent.click(await screen.findByRole("button", { name: "National" }));

    expect(localStorage.getItem("parse.scope.v1")).toBe("world");
  });
});
