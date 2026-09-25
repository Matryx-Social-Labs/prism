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

/** The line that marks the start screen: what can be searched. */
const START = "Search the headline and summary of every record: a story, a person, a place, a ticker or a CVE id.";

function input() {
  return screen.getByRole("searchbox", { name: "Search the record" });
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
    expect(screen.getByText(START)).toBeInTheDocument();
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
    const msg = await screen.findByText(/No records match/);
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

  // No invented suggestions (Design System v2 honesty rule): with trending down
  // there is nothing real to offer, so the start screen offers nothing — no
  // empty "In the news now" heading, no canned queries — and the box still works.
  it("offers no suggestions when trending is down, and the box still searches", async () => {
    fetchTrending.mockRejectedValue(new Error("unreachable"));
    render(<SearchPage />);
    await waitFor(() => expect(fetchTrending).toHaveBeenCalled());
    expect(screen.queryByText("In the news now")).toBeNull();
    expect(screen.queryByRole("button", { name: "RELIANCE" })).toBeNull();
    await userEvent.type(input(), "RELIANCE");
    await waitFor(() => expect(searchEvents).toHaveBeenCalledWith("RELIANCE"));
  });
});

describe("Search — a failed request", () => {
  // REGRESSION: on a rejected searchEvents the page rendered NOTHING. `searched`
  // is set after the await so it stays false, `loading` is false, `results` is
  // empty, and a term of 2+ characters hides the start screen — every branch
  // false. The reader got a blank page with no error and no way to know why.
  it("tells the reader the search failed instead of going blank", async () => {
    searchEvents.mockRejectedValue(new Error("offline"));
    render(<SearchPage />);
    await userEvent.type(screen.getByRole("searchbox"), "reliance");

    expect(await screen.findByText(/Search is unreachable right now/i)).toBeInTheDocument();
    // And it must NOT claim the query simply had no matches — that's a lie.
    expect(screen.queryByText(/No records match/)).not.toBeInTheDocument();
  });

  it("still says 'no match' when the search genuinely returned nothing", async () => {
    searchEvents.mockResolvedValue([]);
    render(<SearchPage />);
    await userEvent.type(screen.getByRole("searchbox"), "zzzz");

    expect(await screen.findByText(/No records match/)).toBeInTheDocument();
    expect(screen.queryByText(/unreachable/i)).not.toBeInTheDocument();
  });

  it("clears the failure when the reader keeps typing, without clearing the box", async () => {
    // Typing MORE rather than clearing is the case that matters: emptying the
    // input resets `failed` through the short-term branch, so a test that clears
    // first passes even with the reset on the search path deleted.
    searchEvents.mockRejectedValueOnce(new Error("offline")).mockResolvedValue([]);
    render(<SearchPage />);
    const box = screen.getByRole("searchbox");
    await userEvent.type(box, "reliance");
    await screen.findByText(/unreachable/i);

    await userEvent.type(box, " jio");
    // Wait for the SETTLED result first. Asserting "no error" directly races the
    // loading state: while `loading` is true the error is hidden anyway, so
    // waitFor passes on that instant and the test guards nothing.
    expect(await screen.findByText(/No records match/)).toBeInTheDocument();
    expect(screen.queryByText(/unreachable/i)).not.toBeInTheDocument();
  });
});

describe("Search — the Records head counts the results", () => {
  it("counts what matched and the sources behind it, on the masthead's dateline", async () => {
    searchEvents.mockResolvedValue([
      item({ id: "a", source_count: 5 }),
      item({ id: "b", title: "Second hit", source_count: 3 }),
    ]);
    render(<SearchPage />);
    await userEvent.type(input(), "freight");
    // Distinct mastheads across the results, not a per-row sum: two rows from
    // the same two outlets count two, and rows that predate outlet data count none.
    expect(await screen.findByText("2 results")).toBeInTheDocument();
  });

  // The API serves a page of 30: a full page may hide more.
  it("prints a full page as 30+, and draws no people section it has no data for", async () => {
    searchEvents.mockResolvedValue(Array.from({ length: 30 }, (_, i) => item({ id: `r${i}` })));
    render(<SearchPage />);
    await userEvent.type(input(), "freight");
    expect(await screen.findByText("30+ results")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Records" })).toBeInTheDocument();
    expect(screen.queryByText(/People and organisations/)).toBeNull();
  });

  it("Esc empties the box, and so does the Clear button", async () => {
    render(<SearchPage />);
    expect(screen.queryByRole("button", { name: "Clear search" })).toBeNull();

    await userEvent.type(input(), "kerala");
    expect(screen.getByRole("button", { name: "Clear search" })).toBeInTheDocument();
    await waitFor(() => expect(searchEvents).toHaveBeenCalledWith("kerala"));

    await userEvent.type(input(), "{Escape}");
    expect(input()).toHaveValue("");
    expect(await screen.findByText(START)).toBeInTheDocument();
  });

  // The strip filters what came back; the API searched everything.
  it("filters the results by sector group in place, and says so when the group is empty", async () => {
    searchEvents.mockResolvedValue([
      item({ id: "a", title: "Rupee slides", sector: "finance" }),
      item({ id: "b", title: "Poll result", sector: "politics" }),
    ]);
    render(<SearchPage />);
    await userEvent.type(input(), "result");
    await screen.findByRole("link", { name: /Poll result/ });
    await userEvent.click(screen.getByRole("button", { name: /Business & Markets/ }));
    expect(screen.getByRole("link", { name: /Rupee slides/ })).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /Poll result/ })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: /Sports/ }));
    expect(screen.getByText(/None of the 2 matches for “result” are in Sports/)).toBeInTheDocument();
  });
});

describe("Search — clearing the box", () => {
  // REGRESSION: clearing WHILE a request was in flight stranded `loading` at
  // true. The effect cleanup cancels, and the in-flight `finally` is guarded by
  // `if (!cancelled)`, so nothing ever reset it — the reader sat on "Searching…"
  // forever and the start screen stayed hidden behind the same !loading gate.
  //
  // The timing is the whole bug: clear AFTER the request settles and the page
  // recovers fine, which is why this has to hold the promise open by hand.
  it("returns to the start screen when cleared mid-request", async () => {
    let release!: (v: unknown) => void;
    searchEvents.mockImplementation(() => new Promise((res) => (release = res)));

    render(<SearchPage />);
    const box = screen.getByRole("searchbox");
    await userEvent.type(box, "kerala");
    expect(await screen.findByText(/Searching/i)).toBeInTheDocument();
    // Wait past the 250ms debounce so the request is genuinely OPEN — clearing
    // before it fires is a different (and already-working) path.
    await waitFor(() => expect(searchEvents).toHaveBeenCalledWith("kerala"));

    // Reader gives up and empties the box while the request is still open.
    await userEvent.clear(box);

    await waitFor(() => expect(screen.queryByText(/Searching/i)).not.toBeInTheDocument());
    expect(screen.getByText(START)).toBeInTheDocument();

    // The abandoned response landing later must not resurrect anything.
    release([]);
    await waitFor(() => expect(screen.getByText(START)).toBeInTheDocument());
    expect(screen.queryByText(/Searching/i)).not.toBeInTheDocument();
  });
});
