import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import PulsePage from "@/app/pulse/page";
import type { MarketDigest } from "@/lib/api";

const fetchDigest = vi.hoisted(() => vi.fn());
const useSession = vi.hoisted(() => vi.fn());
const getWatchlist = vi.hoisted(() => vi.fn());
const follow = vi.hoisted(() => vi.fn());
const unfollow = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", () => ({ fetchDigest }));
vi.mock("@/lib/session", () => ({ useSession }));
vi.mock("@/lib/watchlist", () => ({ getWatchlist, follow, unfollow }));

const BOARD: MarketDigest = {
  window: { start: "2026-09-26T17:30:00+00:00", end: "2026-09-27T17:30:00+00:00" },
  counts: { companies: 2, stories: 3, outlets: 5 },
  companies: [
    {
      id: "e1", headline: "Bank strike deferred after talks", catalyst: "Regulatory action", reading: "positive", confidence: 0.6,
      why: "Service disruption averted", outlets: 4, single_source: false, published_at: "2026-09-27T16:00:00+00:00",
      symbol: "SBIN", exchange: "NSE", company: "State Bank of India",
    },
    {
      id: "e2", headline: "TNPCB tells NGT no expansion at Sun Pharma unit", catalyst: null, reading: null, confidence: null,
      why: null, outlets: 1, single_source: true, published_at: "2026-09-27T15:00:00+00:00",
      symbol: "SUNPHARMA", exchange: "NSE", company: "Sun Pharmaceutical Industries",
    },
  ],
  market_wide: [
    {
      id: "e3", headline: "Mobile retailers warn proposed UPI charges could squeeze margins", catalyst: "Regulatory action",
      reading: "negative", confidence: 0.85, why: "One day UPI acceptance suspension", outlets: 3, single_source: false,
      published_at: "2026-09-27T14:00:00+00:00",
    },
  ],
  read: ["The bank strike and UPI charges lead the board."],
  generated_at: "2026-09-27T17:47:00+00:00",
};

beforeEach(() => {
  fetchDigest.mockReset().mockResolvedValue(BOARD);
  useSession.mockReset().mockReturnValue(null);
  getWatchlist.mockReset().mockResolvedValue([]);
  follow.mockReset().mockResolvedValue([{ id: "w1", kind: "ticker", value: "SBIN" }]);
  unfollow.mockReset().mockResolvedValue([]);
});

describe("Market Pulse — the ticker board", () => {
  it("heads the board with what it counted", async () => {
    render(<PulsePage />);
    expect(await screen.findByRole("heading", { level: 1, name: "Market Pulse" })).toBeInTheDocument();
    expect(screen.getByText("2 companies named · 3 market stories · 5 outlets · last 24 hours")).toBeInTheDocument();
  });

  it("gives each company its symbol, exchange, name, the record, and Prism's reading — never a price", async () => {
    render(<PulsePage />);
    const row = (await screen.findByText("State Bank of India")).closest("li")!;
    const r = within(row);
    expect(r.getByText("SBIN")).toBeInTheDocument();
    expect(r.getByText("NSE")).toBeInTheDocument();
    expect(r.getByRole("link", { name: "Bank strike deferred after talks" })).toHaveAttribute("href", "/story/e1");
    expect(r.getByText("Regulatory action")).toBeInTheDocument();
    expect(r.getByText("Prism’s reading")).toBeInTheDocument();
    expect(r.getByText(/positive · moderate confidence/)).toBeInTheDocument();
    expect(row.textContent).not.toMatch(/0\.6|60/); // the model's float is never printed
    expect(r.getByText(/Service disruption averted/)).toBeInTheDocument();
    expect(r.getByText(/4 outlets/)).toBeInTheDocument();
    expect(row.textContent).not.toMatch(/₹|%|price/i);
  });

  it("marks a company reported by one outlet as one source so far, on a dashed rule", async () => {
    render(<PulsePage />);
    const row = (await screen.findByText("Sun Pharmaceutical Industries")).closest("li")!;
    expect(within(row).getByText(/1 outlet · one source so far/)).toBeInTheDocument();
    expect(row.querySelector(".p-row--single")).not.toBeNull();
    expect(within(row).queryByText("Prism’s reading")).toBeNull();
  });

  it("lists market-wide forces as their own rows, and the read last", async () => {
    render(<PulsePage />);
    const wide = await screen.findByRole("heading", { name: "Market-wide" });
    expect(screen.getByRole("link", { name: /Mobile retailers warn/ })).toHaveAttribute("href", "/story/e3");
    const read = screen.getByRole("heading", { name: "The read" });
    expect(wide.compareDocumentPosition(read) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(screen.getByText("The bank strike and UPI charges lead the board.")).toBeInTheDocument();
  });

  it("leaves the read out when the model wrote none", async () => {
    fetchDigest.mockResolvedValue({ ...BOARD, read: [] });
    render(<PulsePage />);
    await screen.findByText("State Bank of India");
    expect(screen.queryByRole("heading", { name: "The read" })).toBeNull();
  });

  it("says an empty day plainly", async () => {
    fetchDigest.mockResolvedValue({ ...BOARD, counts: { companies: 0, stories: 0, outlets: 0 }, companies: [], market_wide: [], read: [] });
    render(<PulsePage />);
    expect(await screen.findByText("No listed company or market-wide story in the last 24 hours of business reporting")).toBeInTheDocument();
  });

  it("says so when the board could not load, with a way on", async () => {
    fetchDigest.mockResolvedValue(null);
    render(<PulsePage />);
    expect(await screen.findByText("Market Pulse could not load")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /today’s record/ })).toHaveAttribute("href", "/feed");
  });

  // The phone dateline ladder (Masthead): narrower mastheads drop "updated", then the
  // time, never the day (a stalled board must not read as today's); with no board it names the page.
  it("steps the masthead down to the board's day, and names the page when there is no board", async () => {
    const rungs = (c: HTMLElement) => ["l", "m", "s"].map((k) => c.querySelector(`.p-dateline__${k}`)!.textContent);
    const { container, unmount } = render(<PulsePage />);
    await screen.findByText("State Bank of India");
    expect(rungs(container)).toEqual(["27 Sept · updated 23:17 IST", "27 Sept · 23:17 IST", "27 Sept"]);
    unmount();

    fetchDigest.mockResolvedValue(null);
    const empty = render(<PulsePage />);
    await screen.findByText("Market Pulse could not load");
    expect(rungs(empty.container)).toEqual(["Market Pulse", "Market Pulse", "Pulse"]);
  });
});

describe("Following a company from the board", () => {
  it("sends a signed-out reader to sign in and back", async () => {
    render(<PulsePage />);
    expect(await screen.findByRole("link", { name: "Sign in to follow SBIN" })).toHaveAttribute("href", "/signin?next=/pulse");
  });

  it("follows the ticker on the reader's watchlist and says so", async () => {
    useSession.mockReturnValue({ token: "t", userId: "u", email: "a@b.c" });
    render(<PulsePage />);
    fireEvent.click(await screen.findByRole("button", { name: "Follow SBIN" }));
    expect(await screen.findByRole("button", { name: "Following SBIN" })).toHaveAttribute("aria-pressed", "true");
    expect(follow).toHaveBeenCalledWith({ token: "t", userId: "u", email: "a@b.c" }, "ticker", "SBIN");
  });

  it("shows what the reader already follows", async () => {
    useSession.mockReturnValue({ token: "t", userId: "u", email: "a@b.c" });
    getWatchlist.mockResolvedValue([{ id: "w1", kind: "ticker", value: "SUNPHARMA" }]);
    render(<PulsePage />);
    expect(await screen.findByRole("button", { name: "Following SUNPHARMA" })).toBeInTheDocument();
  });
});
