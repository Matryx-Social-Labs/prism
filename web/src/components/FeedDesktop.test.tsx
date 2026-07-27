import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { FeedDesktop } from "@/components/FeedDesktop";
import type { FeedItem } from "@/lib/api";

function item(id: string, sector: string, over: Partial<FeedItem> = {}): FeedItem {
  return {
    id,
    title: `headline ${id}`,
    headline_lang: null,
    available_languages: [],
    summary: null,
    sector,
    subsector: null,
    regions: [],
    image_url: null,
    is_regional: false,
    coverage: null,
    event_type: null,
    source_count: 1,
    cvss_score: null,
    cvss_severity: null,
    kev_listed: false,
    cve_ids: [],
    tickers: [],
    catalyst: null,
    price_impact_direction: null,
    last_updated_at: "2026-07-27T10:00:00Z",
    score: 1,
  } as FeedItem;
}

/** The lead plus its four sidebar stories, which never reach a sector band. */
const HEAD = Array.from({ length: 5 }, (_, n) => item(`head${n}`, "politics"));

describe("desktop feed sector bands", () => {
  // REGRESSION: a sector holding one story got a full-width row of its own — one
  // 160px photo and three empty columns, which reads as a failed load rather than
  // a thin sector. On a live feed that was three rows of six.
  it("collapses one-story sectors into a single shared band", () => {
    render(
      <FeedDesktop
        items={[
          ...HEAD,
          ...Array.from({ length: 4 }, (_, n) => item(`b${n}`, "business")),
          item("sci", "science"),
          item("fin", "finance"),
          item("spo", "sports"),
        ]}
        top={HEAD}
      />,
    );

    expect(screen.getByText("Also filed")).toBeInTheDocument();
    expect(screen.getByText("3 sectors")).toBeInTheDocument();
    // Still one band each for the sectors that can fill a row.
    expect(screen.getByRole("heading", { name: "business" })).toBeInTheDocument();
    // And no full band for the thin ones — they live under Also filed now.
    expect(screen.queryByRole("heading", { name: "science" })).not.toBeInTheDocument();
  });

  it("still reaches every thin sector's story and its sector page", () => {
    render(<FeedDesktop items={[...HEAD, item("sci", "science")]} top={HEAD} />);

    expect(screen.getByText("headline sci")).toHaveAttribute("href", "/story/sci");
    expect(screen.getByText("science")).toHaveAttribute("href", "/sector/science");
  });

  it("omits the band entirely when every sector can fill a row", () => {
    render(
      <FeedDesktop
        items={[...HEAD, ...Array.from({ length: 4 }, (_, n) => item(`b${n}`, "business"))]}
        top={HEAD}
      />,
    );
    expect(screen.queryByText("Also filed")).not.toBeInTheDocument();
  });

  // REGRESSION: the band rail carried a red SINGLE-ORIGIN flag driven by
  // some(single_origin). On an India-only feed that was true for five bands out
  // of six — a warning that fires on nearly everything reports nothing. It stays
  // on the lead, where it describes one story rather than a set.
  it("flags single-origin on the lead only, not on every band", () => {
    const solo = { coverage: { origins: { IN: 2 }, unknown: 0, single_origin: true } };
    render(
      <FeedDesktop
        items={[
          ...HEAD.map((i) => ({ ...i, ...solo }) as FeedItem),
          ...Array.from({ length: 2 }, (_, n) => ({ ...item(`b${n}`, "business"), ...solo }) as FeedItem),
        ]}
        top={HEAD.map((i) => ({ ...i, ...solo }) as FeedItem)}
      />,
    );
    expect(screen.getAllByText("SINGLE-ORIGIN")).toHaveLength(1);
  });
});
