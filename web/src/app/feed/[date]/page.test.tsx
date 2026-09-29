import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";
import type { ArchiveDay, FeedItem } from "@/lib/api";

const fetchArchiveDay = vi.hoisted(() => vi.fn());
const notFound = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_NOT_FOUND"); }));
const redirect = vi.hoisted(() => vi.fn((to: string) => { throw new Error(`NEXT_REDIRECT ${to}`); }));
vi.mock("next/navigation", () => ({ notFound, redirect }));
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchArchiveDay }));

import ArchiveDayPage, { generateMetadata } from "@/app/feed/[date]/page";

const NOINDEX = { index: false, follow: true };
const row = (id: string, subject_path: string) =>
  ({
    id, indexable: true, title: `Record ${id}`, summary: null, sector: null, subsector: null, subject_path, regions: ["IN"], image_url: null,
    is_regional: false, coverage: null, event_type: null, source_count: 2, cvss_score: null, cvss_severity: null, kev_listed: false,
    cve_ids: [], tickers: [], catalyst: null, price_impact_direction: null, headline_lang: null, available_languages: ["en"],
    last_updated_at: "2026-09-27T10:00:00Z", latest_published_at: "2026-09-27T10:00:00Z", score: 0,
    outlets: [{ slug: "a", publisher: "a", name: "A", code: "A", origin: "national", language: "en" }, { slug: "b", publisher: "b", name: "B", code: "B", origin: "national", language: "en" }],
  }) as FeedItem;

const day = (over: Partial<ArchiveDay> = {}): ArchiveDay => ({
  date: "2026-09-27", read: true, whole_day: true, read_from: "2026-09-26T18:33:37Z", read_to: "2026-09-27T18:26:03Z", settled: true,
  records: 2490, multi_outlet: 315, single_source: 2175, languages: 10, indexable: true, floor: 20,
  prev: "2026-09-26", next: "2026-09-28", next_is_today: false,
  items: [row("c1", "civic.crime"), row("p1", "politics.elections")],
  ...over,
});
const NOT_READ = day({ date: "2026-09-10", read: false, whole_day: false, read_from: null, read_to: null, records: null, multi_outlet: null, single_source: null, languages: null, indexable: false, prev: "2026-09-06", next: "2026-09-17", items: [] });

const params = (date: string) => ({ params: Promise.resolve({ date }) });
const page = async (date: string) => new DOMParser().parseFromString(renderToString(await ArchiveDayPage(params(date))), "text/html");

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-09-29T06:00:00Z")); // 11:30 IST on 29 Sep
  fetchArchiveDay.mockReset().mockImplementation(async (date: string) => (date === "2026-09-10" ? NOT_READ : date === "2026-09-27" ? day() : null));
  notFound.mockClear();
  redirect.mockClear();
});
afterEach(() => vi.useRealTimers());

describe("/feed/<date> — which dates are pages", () => {
  it("sends today's date to /feed, temporarily: tomorrow it is yesterday's page", async () => {
    await expect(ArchiveDayPage(params("2026-09-29"))).rejects.toThrow("NEXT_REDIRECT /feed");
    expect(redirect).toHaveBeenCalledWith("/feed");
    // Fetched first, on the young day's hour, so the cached redirect expires with the day.
    expect(fetchArchiveDay).toHaveBeenCalledWith("2026-09-29", 3600);
  });

  it.each(["2026-9-27", "2026-02-30", "yesterday", "27-09-2026"])("is a 404 for a malformed date %j, without asking the API", async (date) => {
    await expect(ArchiveDayPage(params(date))).rejects.toThrow("NEXT_NOT_FOUND");
    expect(fetchArchiveDay).not.toHaveBeenCalled();
  });

  it.each(["2026-07-21", "2026-10-01"])("is a 404 for %s, outside the days Prism has read", async (date) => {
    await expect(ArchiveDayPage(params(date))).rejects.toThrow("NEXT_NOT_FOUND");
  });

  it("fails loudly when the API cannot answer, rather than calling the day unread", async () => {
    fetchArchiveDay.mockRejectedValue(new Error("api down"));
    await expect(ArchiveDayPage(params("2026-09-27"))).rejects.toThrow("api down");
  });

  it("keeps a settled day for a week and a young one for an hour", async () => {
    await page("2026-09-27");
    expect(fetchArchiveDay).toHaveBeenLastCalledWith("2026-09-27", 3600);
    await page("2026-09-10");
    expect(fetchArchiveDay).toHaveBeenLastCalledWith("2026-09-10", 604800);
  });
});

describe("/feed/<date> — a day Prism did not read", () => {
  it("says so, counts nothing and asks not to be indexed", async () => {
    const doc = await page("2026-09-10");
    const text = doc.body.textContent!;
    expect(text).toContain("Prism was not reading on this day, so nothing on it was counted.");
    // No count at all, so no 0 either: nothing was counted.
    expect(text).not.toContain("from two or more outlets");
    expect(text).not.toContain("single-source");
    expect(doc.querySelectorAll("a.p-row")).toHaveLength(0);
    const meta = await generateMetadata(params("2026-09-10"));
    expect(meta.robots).toEqual(NOINDEX);
    expect(meta.description).toBe("Prism was not reading on 10 September 2026, so no record was kept for this day.");
  });
});

describe("/feed/<date> — a day Prism read", () => {
  it("titles the day and asks to be indexed at the floor", async () => {
    const meta = await generateMetadata(params("2026-09-27"));
    expect(meta.title).toBe("India news on 27 September 2026 — the record");
    expect(meta.alternates?.canonical).toBe("/feed/2026-09-27");
    expect("robots" in meta).toBe(false);
    expect(meta.description).toBe("The record for 27 September 2026: 315 stories reported by two or more monitored Indian outlets, by subject, with who said what.");
  });

  it("counts the listed and the unlisted and groups the records by subject in the nav's order", async () => {
    const doc = await page("2026-09-27");
    expect(doc.querySelector("h1")?.textContent).toBe("27 September 2026");
    const text = doc.body.textContent!;
    expect(text).toContain("315 from two or more outlets");
    expect(text).toContain("2175 single-source, counted, not listed");
    expect(text).toContain("10 languages");
    expect([...doc.querySelectorAll("section .p-sechead__title")].map((h) => h.childNodes[0].textContent)).toEqual(["Politics", "Civic & Safety"]);
  });

  it("links the read days either side", async () => {
    const nav = (await page("2026-09-27")).querySelector('nav[aria-label="Other days"]')!;
    expect([...nav.querySelectorAll("a")].map((a) => a.getAttribute("href"))).toEqual(["/feed/2026-09-26", "/archive", "/feed/2026-09-28"]);
  });

  it("says when Prism read only part of the day, in IST", async () => {
    fetchArchiveDay.mockResolvedValue(day({ whole_day: false, read_from: "2026-09-27T05:40:00Z", read_to: "2026-09-27T10:31:00Z" }));
    expect((await page("2026-09-27")).body.textContent).toContain("Prism read from 11:10 to 16:01 IST on this day, not all of it.");
  });

  it("says when Prism stopped reading and has not read since, and does not ask to be indexed", async () => {
    fetchArchiveDay.mockResolvedValue(day({ date: "2026-09-28", whole_day: false, settled: false, read_from: "2026-09-27T18:30:59Z", read_to: "2026-09-28T02:11:14Z", indexable: false, next: null }));
    const doc = await page("2026-09-28");
    expect(doc.body.textContent).toContain("Prism read from 00:00 to 07:41 IST on this day and has not read since, so this record is not complete.");
    expect((await generateMetadata(params("2026-09-28"))).robots).toEqual(NOINDEX);
  });

  it("is a CollectionPage over the day, listing its records, with a breadcrumb", async () => {
    const [collection, crumbs] = [...(await page("2026-09-27")).querySelectorAll('script[type="application/ld+json"]')].map((s) => JSON.parse(s.textContent!));
    expect(collection).toMatchObject({ "@type": "CollectionPage", temporalCoverage: "2026-09-27", mainEntity: { "@type": "ItemList", numberOfItems: 2 } });
    expect(collection.url).toMatch(/\/feed\/2026-09-27$/);
    expect(crumbs.itemListElement.map((i: { name: string }) => i.name)).toEqual(["Prism", "Archive", "27 September 2026"]);
  });
});
