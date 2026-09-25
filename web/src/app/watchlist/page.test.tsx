import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import WatchlistPage from "@/app/watchlist/page";

const useSession = vi.hoisted(() => vi.fn());
const getWatchlist = vi.hoisted(() => vi.fn());
const watchlistEvents = vi.hoisted(() => vi.fn());
const params = vi.hoisted(() => ({ get: vi.fn() }));
const fetchDigest = vi.hoisted(() => vi.fn());
vi.mock("@/lib/session", () => ({ useSession }));
vi.mock("@/lib/api", () => ({ fetchDigest }));
vi.mock("@/lib/watchlist", () => ({ getWatchlist, watchlistEvents, follow: vi.fn(), unfollow: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), useSearchParams: () => params }));

const ev = (id: string, title: string, tickers: string[]) => ({ id, title, summary: null, sector: "finance", tickers, catalyst: null, last_updated_at: "2026-09-16T04:00:00Z" });

beforeEach(() => {
  useSession.mockReset().mockReturnValue({ token: "t", userId: "u", email: "a@b.c" });
  getWatchlist.mockReset().mockResolvedValue([{ id: "1", kind: "ticker", value: "RELIANCE" }, { id: "2", kind: "ticker", value: "TCS" }]);
  watchlistEvents.mockReset().mockResolvedValue([ev("a", "Refining margins widen", ["RELIANCE"]), ev("b", "IT hiring slows", ["TCS"])]);
  params.get.mockReset().mockReturnValue(null);
  fetchDigest.mockReset().mockResolvedValue(null);
  localStorage.setItem("prism.session.v1", JSON.stringify({ token: "t", userId: "u", email: "a@b.c" }));
});

describe("Watchlist — a chart of the reader's signals", () => {
  it("prints every story on the reader's signals with its tickers as chips", async () => {
    render(<WatchlistPage />);
    const row = await screen.findByRole("link", { name: /Refining margins widen/ });
    expect(row).toHaveAttribute("href", "/story/a");
    expect(row.textContent).toMatch(/RELIANCE/);
    expect(screen.getByRole("link", { name: /IT hiring slows/ })).toBeInTheDocument();
  });

  it("narrows to one ticker from ?ticker=, with a way back to all signals", async () => {
    params.get.mockReturnValue("TCS");
    render(<WatchlistPage />);
    expect(await screen.findByRole("link", { name: /IT hiring slows/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Refining margins widen/ })).toBeNull();
    expect(screen.getByRole("link", { name: "All signals" })).toHaveAttribute("href", "/watchlist");
  });

  it("offers the form, not a dead screen, when nothing is followed", async () => {
    getWatchlist.mockResolvedValue([]);
    watchlistEvents.mockResolvedValue([]);
    render(<WatchlistPage />);
    expect(await screen.findByText(/Follow a ticker or sector above/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Follow" })).toBeInTheDocument();
  });

  // The design's Markets read + movers, only when the API has written one.
  it("shows the day's markets reading and its movers when the API has one, and nothing when it has none", async () => {
    fetchDigest.mockResolvedValue({ headline: "Refiners lead a flat day", narrative: "First paragraph.\n\nSecond paragraph.", movers: [{ ticker: "ONGC", note: "Crude up" }], event_ids: ["a", "b"], generated_at: "2026-09-24T10:10:00Z" });
    const { unmount } = render(<WatchlistPage />);
    expect(await screen.findByRole("heading", { name: "Refiners lead a flat day" })).toBeInTheDocument();
    expect(screen.getByText(/written from 2 stories · updated 15:40 IST/)).toBeInTheDocument();
    expect(screen.getByText("First paragraph.")).toBeInTheDocument();
    expect(screen.queryByText("Second paragraph.")).toBeNull();
    expect(screen.getByRole("link", { name: "ONGC" })).toHaveAttribute("href", "/watchlist?ticker=ONGC");
    unmount();

    fetchDigest.mockResolvedValue(null);
    render(<WatchlistPage />);
    await screen.findByRole("link", { name: /Refining margins widen/ });
    expect(screen.queryByText("Markets read")).toBeNull();
  });
});
