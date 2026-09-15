import { describe, expect, it } from "vitest";
import type { EventDetail } from "@/lib/api";
import { ticketFacts } from "@/lib/ticket";

const base = {
  id: "e1",
  title: "t",
  summary: null,
  sector: "finance",
  subsector: null,
  image_url: null,
  regions: [],
  occurred_at: "2026-09-04T18:00:00Z",
  last_updated_at: "2026-09-10T00:00:00Z",
  lens_briefs: {},
  lens_points: {},
  available_lenses: [],
  coverage: { origins: { IN: 6, US: 2 }, unknown: 0 },
  entities: [],
  projection: null,
  sources: [],
  perspectives: [],
  impacts: [],
} as unknown as EventDetail;

const src = (published_at: string | null) =>
  ({ article_id: "a", source_name: "s", source_slug: "s", url: null, title: "t", published_at, stance: null, funding: null });

describe("ticketFacts — the header strip", () => {
  it("prints code · sources · origins · the newest article's IST stamp, in that order", () => {
    const ev = { ...base, sources: [src("2026-09-04T19:55:00Z"), src("2026-09-03T10:00:00Z")] };
    // 19:55Z on the 4th is 01:25 IST on the 5th — the newsroom clock, not the reader's.
    expect(ticketFacts(ev)).toEqual(["BIZ", "2 sources", "IN ×6 · US ×2", "05 SEPT 2026 01:25 IST"]);
  });

  it("says 1 source in the singular and drops a code for the taxonomy's 'other'", () => {
    const ev = { ...base, sector: "other", coverage: null, sources: [src("2026-09-04T19:55:00Z")] };
    expect(ticketFacts(ev)).toEqual(["1 source", "05 SEPT 2026 01:25 IST"]);
  });

  it("falls back to occurred_at, then the ingest clock, when no article carries a date", () => {
    expect(ticketFacts({ ...base, sources: [src(null)] }).at(-1)).toBe("04 SEPT 2026 23:30 IST");
    expect(ticketFacts({ ...base, occurred_at: null }).at(-1)).toBe("10 SEPT 2026 05:30 IST");
  });
});
