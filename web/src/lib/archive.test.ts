import { describe, expect, it } from "vitest";
import type { ArchiveReading, FeedItem } from "@/lib/api";
import { SETTLED_DAY_REVALIDATE, YOUNG_DAY_REVALIDATE, archiveMonths, bySubject, dayRevalidate, dayStrip, istToday, longDay, monthGrid, parseDay } from "@/lib/archive";

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

// There was no way from Today to yesterday's record: /feed/<date> and /archive
// existed, linked only from the desktop footer, which a phone never shows.
describe("dayStrip", () => {
  const today = "2026-11-02";
  // Yesterday back, newest first, as /api/v1/archive gives them; 30 Oct not read.
  const days = ["2026-11-01", "2026-10-31", "2026-10-30", "2026-10-29", "2026-10-28", "2026-10-27", "2026-10-26", "2026-10-25", "2026-10-24", "2026-10-23"]
    .map((d) => day(d, d !== "2026-10-30"));

  it("starts at today on Today, names yesterday, and dates the rest", () => {
    const strip = dayStrip(days, null, today);
    expect(strip.map((d) => d.label)).toEqual(["Today", "Yesterday", "Sat 31 Oct", "Fri 30 Oct", "Thu 29 Oct", "Wed 28 Oct", "Tue 27 Oct"]);
    expect(strip[0]).toMatchObject({ href: "/feed", current: true, count: null });
    expect(strip[1]).toMatchObject({ href: "/feed/2026-11-01", current: false, count: 2 });
  });

  it("does not link a day Prism was not reading, and never prints a 0 for it", () => {
    const off = dayStrip(days, null, today).find((d) => d.date === "2026-10-30");
    expect(off).toMatchObject({ href: null, read: false, count: null });
  });

  it("keeps the day being read in view, three either side", () => {
    const strip = dayStrip(days, "2026-10-26", today);
    expect(strip.map((d) => d.date)).toEqual(["2026-10-29", "2026-10-28", "2026-10-27", "2026-10-26", "2026-10-25", "2026-10-24", "2026-10-23"]);
    expect(strip.filter((d) => d.current).map((d) => d.date)).toEqual(["2026-10-26"]);
  });

  it("dates every day on a day page, whose cache outlives a word like yesterday", () => {
    expect(dayStrip(days, "2026-10-31", today).map((d) => d.label).slice(0, 3)).toEqual(["Today", "Sun 1 Nov", "Sat 31 Oct"]);
  });

  it("stops at the edges instead of running short", () => {
    expect(dayStrip(days, "2026-10-23", today).map((d) => d.date)[6]).toBe("2026-10-23");
    expect(dayStrip(days.slice(0, 2), null, today)).toHaveLength(3);
  });
});

describe("the archive calendar", () => {
  const byDate = new Map([day("2026-10-31", true), day("2026-10-30", false), day("2026-11-01", true)].map((d) => [d.date, d]));

  it("lists the months read, newest first", () => {
    expect(archiveMonths("2026-07-22", "2026-11-02")).toEqual(["2026-11", "2026-10", "2026-09", "2026-08", "2026-07"]);
  });

  it("lays a month out Monday first, each day today, read, not read or outside the archive", () => {
    const weeks = monthGrid("2026-11", byDate, "2026-11-02", "2026-07-22");
    // 1 November 2026 is a Sunday: six blanks before it.
    expect(weeks[0].slice(0, 6).every((c) => c === null)).toBe(true);
    expect(weeks[0][6]).toMatchObject({ date: "2026-11-01", kind: "read" });
    expect(weeks[1][0]).toMatchObject({ date: "2026-11-02", kind: "today" });
    expect(weeks[1][1]).toMatchObject({ date: "2026-11-03", kind: "outside" });
    expect(weeks.every((w) => w.length === 7)).toBe(true);
  });

  it("hatches a day Prism was not reading, and leaves a day before the archive began unmarked", () => {
    const oct = monthGrid("2026-10", byDate, "2026-11-02", "2026-10-30").flat().filter((c) => c);
    expect(oct.find((c) => c!.date === "2026-10-30")).toMatchObject({ kind: "unread" });
    expect(oct.find((c) => c!.date === "2026-10-29")).toMatchObject({ kind: "outside" });
    // In the archive's range but missing from the API's list: not read, never assumed read.
    expect(monthGrid("2026-11", new Map(), "2026-11-02", "2026-07-22").flat().find((c) => c?.date === "2026-11-01")).toMatchObject({ kind: "unread" });
  });
});
