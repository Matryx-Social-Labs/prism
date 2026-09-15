import { describe, expect, it } from "vitest";
import type { FeedItem } from "@/lib/api";
import { bandOrigins, istTime, newsTime, origins, shortDate } from "@/lib/dateline";

function item(id: string, sector: string, over: Partial<FeedItem> = {}): FeedItem {
  return {
    id,
    title: `t-${id}`,
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
    ...over,
  } as FeedItem;
}

describe("the ledger rail", () => {
  it("orders origins by volume and caps them, because the rail is 104px", () => {
    const i = item("a", "politics", {
      coverage: { origins: { AE: 3, IN: 27, UK: 1, US: 9 }, unknown: 0, single_origin: false },
    } as Partial<FeedItem>);
    expect(origins(i)).toBe("IN ×27 · US ×9 · AE ×3");
  });

  it("sums origins across a band", () => {
    const a = item("a", "politics", {
      coverage: { origins: { IN: 4 }, unknown: 0, single_origin: false },
    } as Partial<FeedItem>);
    const b = item("b", "politics", {
      coverage: { origins: { IN: 3, US: 2 }, unknown: 0, single_origin: false },
    } as Partial<FeedItem>);
    expect(bandOrigins([a, b])).toBe("IN ×7 · US ×2");
  });

});

describe("newsTime — the dateline prints when the NEWS happened", () => {
  // events.last_updated_at is set to now() on every projection rebuild, so it
  // records the ingest batch. The feed printed one identical timestamp against
  // every story, and 79% of events (13,657 of 17,385) were more than six hours
  // from their newest article — one by 7.7 hours.
  it("prefers the newest article's publication time", () => {
    expect(
      newsTime({
        latest_published_at: "2026-08-03T13:40:00Z",
        last_updated_at: "2026-08-03T21:19:00Z",
      }),
    ).toBe("2026-08-03T13:40:00Z");
  });

  it("falls back to last_updated_at when no article carries a published_at", () => {
    expect(newsTime({ latest_published_at: null, last_updated_at: "2026-08-03T21:19:00Z" })).toBe(
      "2026-08-03T21:19:00Z",
    );
    expect(newsTime({ last_updated_at: "2026-08-03T21:19:00Z" })).toBe("2026-08-03T21:19:00Z");
  });

  it("renders the news clock, not the ingest clock", () => {
    // 13:40Z is 19:10 IST; the ingest ran at 21:19Z = 02:49 IST the next day.
    const item = {
      latest_published_at: "2026-08-03T13:40:00Z",
      last_updated_at: "2026-08-03T21:19:00Z",
    };
    expect(istTime(newsTime(item))).toBe("19:10");
    expect(istTime(item.last_updated_at)).toBe("02:49"); // what it used to print
  });
});

describe("shortDate", () => {
  it("renders day and short month", () => {
    expect(shortDate("2026-07-27T10:00:00Z")).toBe("27 Jul");
  });

  it("is pinned to IST, so an evening-UTC timestamp is the NEXT Indian day", () => {
    // 20:00 UTC on the 27th is 01:30 IST on the 28th — but still the 27th in
    // UTC, in Europe (CEST) and everywhere west of UTC+4. The inline formatter
    // this replaces had no timeZone, so the same article was dated two ways
    // depending on the reader's machine. A 23:30Z probe would NOT catch a
    // missing pin on a European dev box; this one does.
    expect(shortDate("2026-07-27T20:00:00Z")).toBe("28 Jul");
  });
});
