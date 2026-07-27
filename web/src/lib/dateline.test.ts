import { describe, expect, it } from "vitest";
import type { FeedItem } from "@/lib/api";
import { bandOrigins, bands, lastMoved, origins, sectorEyebrow } from "@/lib/dateline";

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

describe("sector bands", () => {
  // REGRESSION: the first cut capped bands at four and dropped any sector with
  // fewer than four stories. On a real feed that hid five of nine sectors —
  // including cybersecurity, one of the lenses the product is built around.
  it("gives every sector a band, however many there are", () => {
    const items = [
      ...Array.from({ length: 9 }, (_, n) => item(`p${n}`, "politics")),
      ...Array.from({ length: 6 }, (_, n) => item(`b${n}`, "business")),
      ...Array.from({ length: 5 }, (_, n) => item(`c${n}`, "cybersecurity")),
      ...Array.from({ length: 4 }, (_, n) => item(`h${n}`, "health")),
      ...Array.from({ length: 4 }, (_, n) => item(`s${n}`, "sports")),
      ...Array.from({ length: 4 }, (_, n) => item(`e${n}`, "entertainment")),
    ];
    const out = bands(items, new Set());
    expect(out.map((b) => b.sector)).toEqual([
      "politics",
      "business",
      "cybersecurity",
      "health",
      "sports",
      "entertainment",
    ]);
  });

  it("keeps a sector that cannot fill the row rather than hiding it", () => {
    const items = [item("a", "politics"), item("b", "politics"), item("c", "finance")];
    const out = bands(items, new Set());
    const finance = out.find((b) => b.sector === "finance");
    expect(finance).toBeDefined();
    expect(finance!.items).toHaveLength(1); // a short row, not a missing sector
  });

  it("shows at most perBand but reports the real total, so the band can link onward", () => {
    const items = Array.from({ length: 18 }, (_, n) => item(`p${n}`, "politics"));
    const [band] = bands(items, new Set());
    expect(band.items).toHaveLength(4);
    expect(band.total).toBe(18);
  });

  it("never repeats what the lead and its sidebar already used", () => {
    const items = [item("lead", "politics"), item("also", "politics"), item("fresh", "politics")];
    const [band] = bands(items, new Set(["lead", "also"]));
    expect(band.items.map((i) => i.id)).toEqual(["fresh"]);
  });

  it("ignores items with no sector instead of inventing a band for them", () => {
    const items = [item("a", "politics"), { ...item("b", "politics"), sector: null } as FeedItem];
    const out = bands(items, new Set());
    expect(out.map((b) => b.sector)).toEqual(["politics"]);
    expect(out[0].items).toHaveLength(1);
  });
});

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

  it("takes the most recent update as the band's last-moved", () => {
    const a = item("a", "politics", { last_updated_at: "2026-07-27T09:00:00Z" });
    const b = item("b", "politics", { last_updated_at: "2026-07-27T13:05:00Z" });
    expect(lastMoved([a, b])).toBe(lastMoved([b]));
  });

  it("builds the lead eyebrow from sector and subsector", () => {
    expect(sectorEyebrow(item("a", "politics", { subsector: "energy" }))).toBe("POLITICS · ENERGY");
    expect(sectorEyebrow(item("a", "politics"))).toBe("POLITICS");
  });
});
