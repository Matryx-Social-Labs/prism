import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import YouPage from "@/app/you/page";

// jsdom has no viewport, so BOTH trees render: the desktop colophon (`lg:block`)
// and the phone's card stack (`lg:hidden`). Anything the reader set shows up on
// both, hence getAllBy* below — the desktop-only assertions live in their own
// describe at the bottom and can stay singular.

const useSession = vi.hoisted(() => vi.fn());
const clearSession = vi.hoisted(() => vi.fn());
const loadProfile = vi.hoisted(() => vi.fn());
const fetchRegions = vi.hoisted(() => vi.fn());
const getWatchlist = vi.hoisted(() => vi.fn());
const watchlistEvents = vi.hoisted(() => vi.fn());
const useTaxonomy = vi.hoisted(() => vi.fn());

vi.mock("@/lib/session", () => ({ useSession, clearSession }));
vi.mock("@/lib/profile", () => ({ loadProfile }));
vi.mock("@/lib/api", () => ({ fetchRegions }));
vi.mock("@/lib/watchlist", () => ({ getWatchlist, watchlistEvents }));
vi.mock("@/components/ProfileEditor", () => ({ useTaxonomy }));
vi.mock("@/components/ThemeToggle", () => ({ ThemeToggle: () => <button>Theme</button> }));

beforeEach(() => {
  useSession.mockReset().mockReturnValue(null);
  clearSession.mockReset();
  loadProfile.mockReset().mockReturnValue(null);
  fetchRegions.mockReset().mockResolvedValue([{ code: "IN-KL", name: "Kerala" }]);
  getWatchlist.mockReset().mockResolvedValue([]);
  watchlistEvents.mockReset().mockResolvedValue([]);
  useTaxonomy.mockReset().mockReturnValue([{ slug: "politics", name: "Politics", subsectors: [] }]);
});

describe("You — signed out", () => {
  it("presents the reader as a guest and offers sign-in", async () => {
    render(<YouPage />);
    expect(await screen.findByText(/guest/i)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: /sign in/i }).length).toBeGreaterThan(0);
  });

  it("does not ask the API for a watchlist it cannot have", () => {
    render(<YouPage />);
    expect(getWatchlist).not.toHaveBeenCalled();
    expect(watchlistEvents).not.toHaveBeenCalled();
  });
});

describe("You — signed in", () => {
  const SESSION = { token: "t", userId: "u1", email: "sagar@example.com" };
  beforeEach(() => useSession.mockReturnValue(SESSION));

  it("identifies the reader by the local part of their email", async () => {
    render(<YouPage />);
    expect(await screen.findByText("sagar")).toBeInTheDocument();
  });

  it("loads the watchlist", async () => {
    render(<YouPage />);
    expect(getWatchlist).toHaveBeenCalledWith(SESSION);
    expect(watchlistEvents).toHaveBeenCalledWith(SESSION);
  });

  it("lists what the reader follows", async () => {
    getWatchlist.mockResolvedValue([{ kind: "ticker", value: "RELIANCE" }]);
    render(<YouPage />);
    expect(await screen.findAllByText("RELIANCE")).toHaveLength(2);
  });

  it("signs the reader out", async () => {
    render(<YouPage />);
    // Both surfaces offer it; either one has to actually sign the reader out.
    for (const button of await screen.findAllByRole("button", { name: /sign out/i })) {
      clearSession.mockClear();
      await userEvent.click(button);
      expect(clearSession).toHaveBeenCalled();
    }
  });
});

describe("You — Your Parse", () => {
  it("shows the reader's saved lens", async () => {
    loadProfile.mockReturnValue({ lens: "markets" });
    render(<YouPage />);
    expect(await screen.findByText(/Markets/)).toBeInTheDocument();
  });

  it("resolves the region code to a name instead of showing the code", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    render(<YouPage />);
    expect(await screen.findAllByText(/Kerala/)).toHaveLength(2);
  });

  it("survives the regions lookup failing", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    fetchRegions.mockRejectedValue(new Error("down"));
    render(<YouPage />);
    expect((await screen.findAllByText(/Your Parse/i)).length).toBeGreaterThan(0);
  });

  it("defaults to English when no language is saved", async () => {
    loadProfile.mockReturnValue({});
    render(<YouPage />);
    // Languages render in their own script; English's token is "EN".
    expect(await screen.findAllByText("EN")).toHaveLength(2);
  });

  it("renders a saved language in its own script", async () => {
    loadProfile.mockReturnValue({ languages: ["hi", "ta"] });
    render(<YouPage />);
    expect(await screen.findByText("हिंदी")).toBeInTheDocument();
    expect(screen.getByText("தமிழ்")).toBeInTheDocument();
  });

  it("names an interest through the taxonomy, including its subsector", async () => {
    loadProfile.mockReturnValue({ interests: ["politics:elections"] });
    render(<YouPage />);
    expect(await screen.findAllByText(/Politics · elections/)).toHaveLength(2);
  });
});

describe("You — the desktop colophon", () => {
  // Only the desktop composition renders these strings, so singular queries hold.
  it("reads as a colophon of what the reader actually set", async () => {
    useSession.mockReturnValue({ token: "t", userId: "u1", email: "sagar@example.com" });
    loadProfile.mockReturnValue({ lens: "markets", state: "IN-KL", languages: ["hi"] });
    render(<YouPage />);

    expect(await screen.findByText("How your Parse is made")).toBeInTheDocument();
    expect(screen.getByText(/Signed in as sagar@example.com/)).toBeInTheDocument();
    // The full lens name, not the phone's abbreviated pill.
    expect(screen.getByText("Finance / Trader")).toBeInTheDocument();
  });

  it("says what is unset instead of leaving a blank line", async () => {
    loadProfile.mockReturnValue({ lens: "reader" });
    render(<YouPage />);
    expect(await screen.findByText("Nothing chosen yet")).toBeInTheDocument();
    expect(screen.getByText("All India")).toBeInTheDocument();
  });

  it("offers a guest the way in, not a sign-out", async () => {
    render(<YouPage />);
    expect(await screen.findByText(/nothing is synced/)).toBeInTheDocument();
    expect(screen.getByText("Sign in to follow tickers and sectors")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /sign out/i })).not.toBeInTheDocument();
  });
});
