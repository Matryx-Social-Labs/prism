import { describe, expect, it } from "vitest";
import type { ArchiveReading, FeedItem } from "@/lib/api";
import { SETTLED_DAY_REVALIDATE, YOUNG_DAY_REVALIDATE, archiveRows, bySubject, dayRevalidate, istToday, longDay, parseDay } from "@/lib/archive";

describe("parseDay", () => {
  it("takes a strict yyyy-mm-dd that names a real day", () => {
    expect(parseDay("2026-09-27")).toBe("2026-09-27");
    expect(parseDay("2024-02-29")).toBe("2024-02-29");
  });

  it.each(["2026-9-27", "27-09-2026", "2026-02-30", "2026-13-01", "2026-09-27T00:00", "20260927", "today", ""])("refuses %j", (s) => {
    expect(parseDay(s)).toBeNull();
  });
});

describe("the IST calendar", () => {
  it("is today in India, not the server's zone", () => {
    // 20:00 UTC on the 28th is 01:30 on the 29th in India.
    expect(istToday(new Date("2026-09-28T20:00:00Z"))).toBe("2026-09-29");
    expect(istToday(new Date("2026-09-28T18:00:00Z"))).toBe("2026-09-28");
  });

  it("prints a date in words, with no zone to get wrong", () => {
    expect(longDay("2026-09-27")).toBe("27 September 2026");
    expect(longDay("2026-07-01")).toBe("1 July 2026");
  });

  it("keeps a young day on an hour's clock and a settled one on a week's", () => {
    expect(dayRevalidate("2026-09-28", "2026-09-29")).toBe(YOUNG_DAY_REVALIDATE);
    expect(dayRevalidate("2026-09-27", "2026-09-29")).toBe(YOUNG_DAY_REVALIDATE);
    expect(dayRevalidate("2026-09-26", "2026-09-29")).toBe(SETTLED_DAY_REVALIDATE);
    // A date not yet reached answers 404 now, and must not stay a 404 for a week.
    expect(dayRevalidate("2026-10-05", "2026-09-29")).toBe(YOUNG_DAY_REVALIDATE);
  });
});

const item = (id: string, subject_path: string | null, sector: string | null = null) => ({ id, subject_path, sector }) as unknown as FeedItem;

describe("bySubject", () => {
  it("groups under the nav's roots in the nav's order, keeping each group's order", () => {
    const groups = bySubject([item("c1", "civic.crime"), item("p1", "politics.elections"), item("p2", "politics"), item("b1", null, "finance")]);
    expect(groups.map((g) => [g.name, g.href, g.items.map((i) => i.id)])).toEqual([
      ["Politics", "/sector/politics", ["p1", "p2"]],
      ["Business & Markets", "/sector/business", ["b1"]],
      ["Civic & Safety", "/subject/civic", ["c1"]],
    ]);
  });

  it("says a record has no subject rather than calling it Other", () => {
    const groups = bySubject([item("x", null, "other")]);
    expect(groups.map((g) => g.name)).toEqual(["Not yet placed in a subject"]);
    expect(groups.some((g) => /other/i.test(g.name))).toBe(false);
  });
});

const day = (date: string, read: boolean): ArchiveReading => ({
  date, read, whole_day: read, read_from: null, read_to: null, settled: true, records: read ? 5 : null, multi_outlet: read ? 2 : null, indexable: false,
});

describe("archiveRows", () => {
  it("folds each run of days Prism was not reading into one row", () => {
    const rows = archiveRows([day("2026-09-17", true), day("2026-09-16", false), day("2026-09-15", false), day("2026-09-14", false), day("2026-09-06", true), day("2026-09-05", false)]);
    expect(rows).toEqual([
      { kind: "day", day: day("2026-09-17", true) },
      { kind: "gap", from: "2026-09-14", to: "2026-09-16" },
      { kind: "day", day: day("2026-09-06", true) },
      { kind: "gap", from: "2026-09-05", to: "2026-09-05" },
    ]);
  });
});
