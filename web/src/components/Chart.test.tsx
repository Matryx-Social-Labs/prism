import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Chart, chartOrder } from "@/components/Chart";
import type { FeedItem } from "@/lib/api";

function item(over: Partial<FeedItem> = {}): FeedItem {
  return {
    id: "e1",
    title: "Story",
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
    source_count: 4,
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
  } as FeedItem;
}

beforeEach(() => localStorage.clear());
afterEach(() => localStorage.clear());

describe("chartOrder — the weight of evidence leads", () => {
  // The API returns newest-first; the chart's rule is most-corroborated first.
  // A story eight outlets reported outranks one that one outlet reported five
  // minutes ago, and the order is the same for every reader (D2).
  it("sorts by source count, then by the news's own time", () => {
    const items = [
      item({ id: "one-source-newest", source_count: 1, latest_published_at: "2026-09-05T18:00:00Z" }),
      item({ id: "eight-older", source_count: 8, latest_published_at: "2026-09-05T10:00:00Z" }),
      item({ id: "eight-newer", source_count: 8, latest_published_at: "2026-09-05T12:00:00Z" }),
    ];
    expect(chartOrder(items).map((i) => i.id)).toEqual(["eight-newer", "eight-older", "one-source-newest"]);
  });

  it("falls back to last_updated_at when the news carries no published time", () => {
    const items = [
      item({ id: "a", source_count: 2, latest_published_at: null, last_updated_at: "2026-09-05T10:00:00Z" }),
      item({ id: "b", source_count: 2, latest_published_at: null, last_updated_at: "2026-09-05T11:00:00Z" }),
    ];
    expect(chartOrder(items).map((i) => i.id)).toEqual(["b", "a"]);
  });

  it("does not mutate the API's list", () => {
    const items = [item({ id: "a", source_count: 1 }), item({ id: "b", source_count: 9 })];
    chartOrder(items);
    expect(items.map((i) => i.id)).toEqual(["a", "b"]);
  });
});

describe("Chart — the list", () => {
  it("prints the rows in chart order with the first as the lead", () => {
    render(<Chart items={[item({ id: "a", title: "Thin", source_count: 1 }), item({ id: "b", title: "Corroborated", source_count: 9 })]} emptyLabel="none" />);
    const rows = screen.getAllByRole("listitem");
    expect(within(rows[0]).getByText("Corroborated")).toBeInTheDocument();
    expect(within(rows[1]).getByText("Thin")).toBeInTheDocument();
  });

  it("names the subject when there is nothing, and offers no dead link", () => {
    // REGRESSION: the empty state and the foot linked /feed/yesterday, a route
    // the redesign never carried over — a 404 on the one path a reader took
    // when the chart was empty.
    render(<Chart items={[]} emptyLabel="No Sports stories on today's chart" />);
    expect(screen.getByText(/No Sports stories on today's chart/)).toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /yesterday/i })).toBeNull();
    expect(screen.queryByRole("list")).toBeNull();
  });
});

describe("Chart — reading position persists", () => {
  it("remembers the row the reader opened and marks it on return", async () => {
    const items = [item({ id: "a", title: "First" }), item({ id: "b", title: "Second" })];
    const { unmount } = render(<Chart items={items} emptyLabel="none" />);
    await userEvent.click(screen.getByText("Second"));
    unmount();

    render(<Chart items={items} emptyLabel="none" />);
    expect(screen.getByRole("link", { name: /Second/ })).toHaveAttribute("aria-current", "true");
    expect(screen.getByRole("link", { name: /First/ })).not.toHaveAttribute("aria-current");
  });
});
