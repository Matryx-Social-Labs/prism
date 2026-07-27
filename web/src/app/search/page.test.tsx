import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import SearchPage from "@/app/search/page";
import type { FeedItem } from "@/lib/api";

const searchEvents = vi.hoisted(() => vi.fn());
const fetchTrending = vi.hoisted(() => vi.fn());
// ONE object for the whole file. `router` is in the search effect's dep array,
// so a mock that built a fresh object per render would re-run the effect on
// every render and spin forever.
const router = vi.hoisted(() => ({ replace: vi.fn() }));
const params = vi.hoisted(() => ({ get: vi.fn() }));

vi.mock("@/lib/api", () => ({ searchEvents, fetchTrending }));
vi.mock("next/navigation", () => ({
  useRouter: () => router,
  useSearchParams: () => params,
}));

// The debounce is a real 250ms timer; these tests run on real timers and let
// waitFor (1s budget) absorb it, so user-event's own async stepping stays honest.
const DEBOUNCE_SETTLED = 400;

function item(over: Partial<FeedItem> = {}): FeedItem {
  return {
    id: "e1",
    title: "Monsoon freight corridor reopens",
    headline_lang: "en",
    available_languages: ["en"],
    summary: null,
    sector: "logistics",
    subsector: null,
    regions: [],
    image_url: null,
    is_regional: false,
    coverage: null,
    event_type: null,
    source_count: 4,
    cvss_score: null,
    cvss_severity: null,
    kev_listed: false,
    cve_ids: [],
    tickers: [],
    catalyst: null,
    price_impact_direction: null,
    last_updated_at: new Date().toISOString(),
    score: 1,
    ...over,
  };
}

function input() {
  return screen.getByRole("textbox", { name: "Search stories, entities and sources" });
}

beforeEach(() => {
  searchEvents.mockReset().mockResolvedValue([]);
  fetchTrending.mockReset().mockResolvedValue([]);
  router.replace.mockReset();
  params.get.mockReset().mockReturnValue(null);
});

describe("Search — querying", () => {
  it("searches for what the reader typed", async () => {
    render(<SearchPage />);
    await userEvent.type(input(), "reliance jio");
    await waitFor(() => expect(searchEvents).toHaveBeenCalledWith("reliance jio"));
  });

  it("runs the query in the URL without the reader typing anything", async () => {
    params.get.mockReturnValue("cve-2026-62144");
    render(<SearchPage />);
    expect(input()).toHaveValue("cve-2026-62144");
    await waitFor(() => expect(searchEvents).toHaveBeenCalledWith("cve-2026-62144"));
  });

  it("does not fire a request on a single character", async () => {
    render(<SearchPage />);
    await userEvent.type(input(), "r");
    await new Promise((r) => setTimeout(r, DEBOUNCE_SETTLED));
    expect(searchEvents).not.toHaveBeenCalled();
    // Still on the start screen, not a half-committed search.
    expect(screen.getByText("Trending entities")).toBeInTheDocument();
  });

  it("writes the query back to the URL, escaped", async () => {
    render(<SearchPage />);
    await userEvent.type(input(), "tata steel");
    await waitFor(() =>
      expect(router.replace).toHaveBeenCalledWith("/search?q=tata%20steel", { scroll: false })
    );
  });

  // A slow response for a query the reader has already moved on from must not
  // land on top of the newer results.
  it("ignores a late response for an abandoned query", async () => {
    let landStale: (v: FeedItem[]) => void = () => {};
    searchEvents.mockImplementation((term: string) =>
      term === "old query"
        ? new Promise<FeedItem[]>((res) => {
            landStale = res;
          })
        : Promise.resolve([item({ id: "fresh", title: "Fresh result headline" })])
    );

    render(<SearchPage />);
    await userEvent.type(input(), "old query");
    await waitFor(() => expect(searchEvents).toHaveBeenCalledWith("old query"));

    await userEvent.clear(input());
    await userEvent.type(input(), "new query");
    expect(await screen.findByText("Fresh result headline")).toBeInTheDocument();

    landStale([item({ id: "stale", title: "Stale result headline" })]);
    await new Promise((r) => setTimeout(r, 50));

    expect(screen.queryByText("Stale result headline")).not.toBeInTheDocument();
    expect(screen.getByText("Fresh result headline")).toBeInTheDocument();
  });
});

describe("Search — results", () => {
  it("renders each hit as a link to its story", async () => {
    searchEvents.mockResolvedValue([item()]);
    render(<SearchPage />);
    await userEvent.type(input(), "freight");
    const link = await screen.findByRole("link", { name: /Monsoon freight corridor reopens/ });
    expect(link).toHaveAttribute("href", "/story/e1");
  });

  it("says nothing matched instead of showing a blank screen", async () => {
    searchEvents.mockResolvedValue([]);
    render(<SearchPage />);
    await userEvent.type(input(), "zzzqqq");
    const msg = await screen.findByText(/No stories match/);
    expect(msg).toHaveTextContent("zzzqqq");
  });

  // REGRESSION: a network failure REJECTS searchEvents, and an escaped rejection
  // left setLoading(true) — "Searching…" forever on a flaky mobile connection.
  it("stops searching when the request fails", async () => {
    searchEvents.mockRejectedValue(new Error("offline"));
    render(<SearchPage />);
    await userEvent.type(input(), "of");
    expect(screen.getByText("Searching…")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText("Searching…")).not.toBeInTheDocument());
  });
});

describe("Search — start screen", () => {
  it("offers real trending entities, once each, and searches the one tapped", async () => {
    fetchTrending.mockResolvedValue([
      { cast: ["Adani Group", "SEBI"] },
      { cast: ["Adani Group"] },
      { cast: [] },
    ]);
    render(<SearchPage />);

    const chip = await screen.findByRole("button", { name: "Adani Group" });
    expect(screen.getAllByRole("button", { name: "Adani Group" })).toHaveLength(1);
    expect(fetchTrending).toHaveBeenCalledWith({ limit: 6 });

    await userEvent.click(chip);
    expect(input()).toHaveValue("Adani Group");
    await waitFor(() => expect(searchEvents).toHaveBeenCalledWith("Adani Group"));
  });

  it("still offers the canned suggestions when trending is down", async () => {
    fetchTrending.mockRejectedValue(new Error("unreachable"));
    render(<SearchPage />);
    await userEvent.click(await screen.findByRole("button", { name: "RELIANCE" }));
    await waitFor(() => expect(searchEvents).toHaveBeenCalledWith("RELIANCE"));
  });
});
