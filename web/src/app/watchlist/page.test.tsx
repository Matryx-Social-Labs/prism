import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import WatchlistPage from "@/app/watchlist/page";

const useSession = vi.hoisted(() => vi.fn());
const getWatchlist = vi.hoisted(() => vi.fn());
const watchlistEvents = vi.hoisted(() => vi.fn());
const follow = vi.hoisted(() => vi.fn());
const unfollow = vi.hoisted(() => vi.fn());
const params = vi.hoisted(() => ({ get: vi.fn() }));
const fetchDigest = vi.hoisted(() => vi.fn());
vi.mock("@/lib/session", () => ({ useSession }));
vi.mock("@/lib/api", () => ({ fetchDigest }));
vi.mock("@/lib/watchlist", () => ({ getWatchlist, watchlistEvents, follow, unfollow }));
vi.mock("next/navigation", () => ({ useRouter: () => ({ replace: vi.fn() }), useSearchParams: () => params }));

const ev = (id: string, title: string, tickers: string[]) => ({ id, title, summary: null, sector: "finance", tickers, catalyst: null, last_updated_at: "2026-09-16T04:00:00Z" });

beforeEach(() => {
  useSession.mockReset().mockReturnValue({ token: "t", userId: "u", email: "a@b.c" });
  getWatchlist.mockReset().mockResolvedValue([{ id: "1", kind: "ticker", value: "RELIANCE" }, { id: "2", kind: "ticker", value: "TCS" }]);
  watchlistEvents.mockReset().mockResolvedValue([ev("a", "Refining margins widen", ["RELIANCE"]), ev("b", "IT hiring slows", ["TCS"])]);
  params.get.mockReset().mockReturnValue(null);
  fetchDigest.mockReset().mockResolvedValue(null);
  follow.mockReset();
  unfollow.mockReset();
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
    // Nothing on TCS today: the date it was last named comes from the story in hand, not a guess.
    expect(screen.getByText("No stories on TCS today")).toBeInTheDocument();
    expect(screen.getByText("The last story naming TCS was updated on 16 Sept.")).toBeInTheDocument();
  });

  it("says when nothing on the signals moved today, and keeps the earlier stories below", async () => {
    render(<WatchlistPage />);
    expect(await screen.findByText("No stories on your signals today")).toBeInTheDocument();
    expect(screen.getByText(/No story on RELIANCE or TCS has been updated since midnight IST/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Refining margins widen/ })).toBeInTheDocument();
  });

  it("checks a symbol in words before it is sent, and sends a good one upper-cased", async () => {
    follow.mockResolvedValue([{ id: "3", kind: "ticker", value: "INFY" }]);
    render(<WatchlistPage />);
    const field = await screen.findByRole("textbox", { name: "NSE or BSE symbol" });
    await userEvent.type(field, "reli ance");
    await userEvent.click(screen.getByRole("button", { name: "Follow" }));
    expect(screen.getByText(/A symbol is letters and numbers/)).toBeInTheDocument();
    expect(follow).not.toHaveBeenCalled();

    await userEvent.clear(field);
    await userEvent.type(field, "infy");
    await userEvent.click(screen.getByRole("button", { name: "Follow" }));
    expect(follow).toHaveBeenCalledWith(expect.anything(), "ticker", "INFY");
  });

  it("follows a subject as every sector it groups, and shows it as one chip", async () => {
    getWatchlist.mockResolvedValue([]);
    follow.mockResolvedValueOnce([{ id: "4", kind: "sector", value: "business" }]).mockResolvedValueOnce([
      { id: "4", kind: "sector", value: "business" },
      { id: "5", kind: "sector", value: "finance" },
    ]);
    render(<WatchlistPage />);
    await userEvent.click(await screen.findByRole("tab", { name: "Sector" }));
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Subject" }), "business");
    await userEvent.click(screen.getByRole("button", { name: "Follow" }));
    expect(follow.mock.calls.map((c) => c.slice(1))).toEqual([["sector", "business"], ["sector", "finance"]]);
    expect(await screen.findByRole("button", { name: "Stop following Business & Markets" })).toBeInTheDocument();
    expect(within(screen.getByRole("list", { name: "Following" })).getAllByText("Business & Markets")).toHaveLength(1);
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
