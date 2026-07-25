import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import YouPage from "@/app/you/page";

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
    expect(await screen.findByText("RELIANCE")).toBeInTheDocument();
  });

  it("signs the reader out", async () => {
    render(<YouPage />);
    await userEvent.click(await screen.findByRole("button", { name: /sign out/i }));
    expect(clearSession).toHaveBeenCalled();
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
    expect(await screen.findByText(/Kerala/)).toBeInTheDocument();
  });

  it("survives the regions lookup failing", async () => {
    loadProfile.mockReturnValue({ state: "IN-KL" });
    fetchRegions.mockRejectedValue(new Error("down"));
    render(<YouPage />);
    expect(await screen.findByText(/Your Parse/i)).toBeInTheDocument();
  });

  it("defaults to English when no language is saved", async () => {
    loadProfile.mockReturnValue({});
    render(<YouPage />);
    // Languages render in their own script; English's token is "EN".
    expect(await screen.findByText("EN")).toBeInTheDocument();
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
    expect(await screen.findByText(/Politics · elections/)).toBeInTheDocument();
  });
});
