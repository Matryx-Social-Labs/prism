import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import YouPage from "@/app/you/page";

// /you is the reservation form plus Following and Account. @/lib/profile and
// the picks codec stay REAL: the localStorage round-trip is the thing under test.
const useSession = vi.hoisted(() => vi.fn());
const clearSession = vi.hoisted(() => vi.fn());
const fetchLanguages = vi.hoisted(() => vi.fn());
const fetchRegions = vi.hoisted(() => vi.fn());
const fetchTaxonomy = vi.hoisted(() => vi.fn());
const fetchProfessions = vi.hoisted(() => vi.fn());
const fetchLenses = vi.hoisted(() => vi.fn());
const getWatchlist = vi.hoisted(() => vi.fn());
const watchlistEvents = vi.hoisted(() => vi.fn());
const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock("@/lib/session", () => ({ useSession, clearSession, fetchLanguages }));
vi.mock("@/lib/api", () => ({ fetchRegions, fetchTaxonomy, fetchProfessions, fetchLenses }));
vi.mock("@/lib/watchlist", () => ({ getWatchlist, watchlistEvents }));
vi.mock("@/components/ThemeToggle", () => ({ ThemeToggle: () => <button>Theme</button> }));
vi.mock("next/navigation", () => ({ useRouter: () => router }));

const KEY = "prism.profile.v1";
const SAVED = { lens: "markets", region: "IN", state: "IN-KL", interests: ["politics:elections"], languages: ["hi", "en"] };
const saved = () => JSON.parse(localStorage.getItem(KEY) ?? "null");
const stateSelect = () => screen.getByRole("combobox", { name: "Your state" });
const save = () => userEvent.click(screen.getByRole("button", { name: /Save and re-sort my chart/ }));
// Everything the form pulls has landed, otherwise a click races the taxonomy.
const settled = async () => {
  await screen.findByRole("option", { name: "Karnataka" });
  await screen.findByRole("button", { name: /Politics/ });
  await screen.findByRole("button", { name: /^English/ });
};

beforeEach(() => {
  localStorage.clear();
  useSession.mockReset().mockReturnValue(null);
  clearSession.mockReset();
  router.push.mockReset();
  fetchRegions.mockReset().mockResolvedValue([{ code: "IN-KL", name: "Kerala", covered: true }, { code: "IN-KA", name: "Karnataka", covered: false }]);
  fetchTaxonomy.mockReset().mockResolvedValue([
    { slug: "politics", name: "Politics", subsectors: [{ slug: "elections", name: "Elections" }] },
    { slug: "business", name: "Business", subsectors: [] },
    { slug: "finance", name: "Finance", subsectors: [{ slug: "markets", name: "Stock market" }] },
  ]);
  fetchProfessions.mockReset().mockResolvedValue([
    { group: "Finance", options: [{ slug: "trader", label: "Trader", lens: "markets", interests: ["finance"] }] },
  ]);
  fetchLanguages.mockReset().mockResolvedValue({
    languages: [{ code: "en", name: "English", native: "English" }, { code: "hi", name: "Hindi", native: "हिंदी" }],
    default: ["en"],
  });
  fetchLenses.mockReset().mockResolvedValue([]);
  getWatchlist.mockReset().mockResolvedValue([]);
  watchlistEvents.mockReset().mockResolvedValue([]);
});

describe("You — round-trip", () => {
  it("re-saves a stored profile unchanged", async () => {
    localStorage.setItem(KEY, JSON.stringify(SAVED));
    render(<YouPage />);
    await settled();
    await save();
    expect(saved()).toEqual(SAVED);
    expect(router.push).toHaveBeenCalledWith("/feed");
  });

  it("starts from the defaults when nothing is stored", async () => {
    render(<YouPage />);
    await settled();
    await save();
    expect(saved()).toEqual({ lens: "reader", region: "IN", state: null, interests: [], languages: ["en"] });
  });

  it("persists a changed state, profession and subject", async () => {
    render(<YouPage />);
    await settled();
    await userEvent.selectOptions(stateSelect(), "IN-KA");
    await userEvent.selectOptions(screen.getByRole("combobox", { name: "Your profession" }), "trader");
    await userEvent.click(screen.getByRole("button", { name: /Politics/ }));
    await save();
    // The trader's default subject was pre-set because the reader had none; then Politics was added.
    expect(saved()).toEqual({ lens: "markets", region: "IN", state: "IN-KA", interests: ["finance", "politics"], languages: ["en"] });
  });

  it("does not save what the reader cancelled", async () => {
    localStorage.setItem(KEY, JSON.stringify(SAVED));
    render(<YouPage />);
    await settled();
    await userEvent.selectOptions(stateSelect(), "IN-KA");
    await userEvent.click(screen.getByRole("link", { name: "Cancel" }));
    expect(saved()).toEqual(SAVED);
  });
});

describe("You — subjects are the six, picks stay the pipeline's ten", () => {
  it("following Business & Markets follows both sectors, and a beat narrows one of them", async () => {
    render(<YouPage />);
    await settled();
    await userEvent.click(screen.getByRole("button", { name: /Business & Markets/ }));
    await userEvent.click(screen.getByRole("button", { name: "Stock market" }));
    await save();
    expect(saved().interests).toEqual(["business", "finance:markets"]);
  });

  it("unfollowing a subject drops every sector it groups", async () => {
    localStorage.setItem(KEY, JSON.stringify({ ...SAVED, interests: ["business", "finance:markets"] }));
    render(<YouPage />);
    await settled();
    await userEvent.click(screen.getByRole("button", { name: /Business & Markets/ }));
    await save();
    expect(saved().interests).toEqual([]);
  });
});

describe("You — languages", () => {
  it("saves the reader's preference order, not the order of the options", async () => {
    render(<YouPage />);
    await settled();
    await userEvent.click(screen.getByRole("button", { name: /^Hindi/ }));
    await userEvent.click(screen.getByRole("button", { name: /^English, preference 1/ })); // drop English
    await userEvent.click(screen.getByRole("button", { name: /^English$/ })); // re-add it last
    await save();
    expect(saved().languages).toEqual(["hi", "en"]);
  });

  it("will not let the reader remove their last language", async () => {
    render(<YouPage />);
    await settled();
    await userEvent.click(screen.getByRole("button", { name: /^English, preference 1/ }));
    expect(screen.getByRole("button", { name: /^English, preference 1/ })).toHaveAttribute("aria-pressed", "true");
  });
});

describe("You — when an API is down", () => {
  it("does not take the page down when regions fail to load, and the state select keeps its name", async () => {
    fetchRegions.mockRejectedValue(new Error("down"));
    render(<YouPage />);
    await screen.findByRole("button", { name: /Politics/ });
    expect(stateSelect()).toBeInTheDocument();
  });
});

describe("You — identity, following, account", () => {
  it("presents a guest as browsing without an account and offers sign-in, asking for no watchlist", async () => {
    render(<YouPage />);
    expect(await screen.findByText(/no account needed/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Sign in to follow/ })).toBeInTheDocument();
    expect(getWatchlist).not.toHaveBeenCalled();
  });

  it("names the signed-in reader, lists what they follow, and signs them out", async () => {
    useSession.mockReturnValue({ token: "t", userId: "u", email: "asha@example.in" });
    getWatchlist.mockResolvedValue([{ id: "1", kind: "ticker", value: "RELIANCE" }]);
    render(<YouPage />);
    expect(await screen.findByText(/Signed in as asha@example.in/)).toBeInTheDocument();
    expect(await screen.findByText("RELIANCE")).toBeInTheDocument();
    Object.defineProperty(window, "location", { value: { href: "" }, writable: true });
    await userEvent.click(screen.getByRole("button", { name: "Sign out" }));
    expect(clearSession).toHaveBeenCalled();
    await waitFor(() => expect(window.location.href).toBe("/feed"));
  });
});
