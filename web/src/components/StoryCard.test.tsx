import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { itemMeta, timeAgo, StoryRowCard } from "@/components/StoryCard";
import type { FeedItem } from "@/lib/api";

const NOW = new Date("2026-07-25T12:00:00Z");
const ago = (ms: number) => new Date(NOW.getTime() - ms).toISOString();
const HOUR = 3_600_000;

function item(over: Partial<FeedItem> = {}): FeedItem {
  return {
    id: "e1",
    title: "Crime Branch to re-arrest Dr. M.K Ram",
    headline_lang: null,
    available_languages: [],
    summary: "s",
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
    last_updated_at: ago(2 * HOUR),
    score: 1,
    ...over,
  } as FeedItem;
}

beforeEach(() => vi.setSystemTime(NOW));
afterEach(() => vi.useRealTimers());

describe("timeAgo", () => {
  it.each([
    [0, "just now"],
    [59 * 60_000, "just now"],
    [HOUR, "1h ago"],
    [5 * HOUR, "5h ago"],
    [23 * HOUR, "23h ago"],
    [24 * HOUR, "1d ago"],
    [72 * HOUR, "3d ago"],
  ])("renders %i ms ago as %s", (delta, expected) => {
    expect(timeAgo(ago(delta))).toBe(expected);
  });

  // The story page SSRs this, so server and client compute different values —
  // the reason that span carries suppressHydrationWarning.
  it("is a pure function of the clock", () => {
    const iso = ago(3 * HOUR);
    expect(timeAgo(iso)).toBe("3h ago");
    vi.setSystemTime(new Date(NOW.getTime() + 2 * HOUR));
    expect(timeAgo(iso)).toBe("5h ago");
  });
});

describe("itemMeta", () => {
  it("pluralizes the source count", () => {
    expect(itemMeta(item({ source_count: 1 }))).toBe("1 source · 2h ago");
    expect(itemMeta(item({ source_count: 4 }))).toBe("4 sources · 2h ago");
  });
});

describe("StoryRowCard", () => {
  it("links the whole row to the story", () => {
    render(<StoryRowCard item={item()} lens="reader" />);
    expect(screen.getByRole("link")).toHaveAttribute("href", "/story/e1");
  });

  it("renders the headline and its provenance", () => {
    render(<StoryRowCard item={item()} lens="reader" />);
    expect(screen.getByText(/Crime Branch to re-arrest/)).toBeInTheDocument();
    expect(screen.getByText(/4 sources · 2h ago/)).toBeInTheDocument();
  });

  it("renders no thumbnail when the story has no image", () => {
    const { container } = render(<StoryRowCard item={item({ image_url: null })} lens="reader" />);
    expect(container.querySelector("img")).toBeNull();
  });

  it("renders a thumbnail when the story has one", () => {
    const { container } = render(
      <StoryRowCard item={item({ image_url: "https://cdn.example/a.jpg" })} lens="reader" />
    );
    expect(container.querySelector("img")).not.toBeNull();
  });
});
