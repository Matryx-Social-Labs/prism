import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";

// The two page families of audit 02 (P1-1 state hubs, P1-2 day archive) as the
// rest of the site sees them: the sitemap, the two indexes, the entity address
// a state hub replaces, and the title templates (P2-2, P2-3).

const permanentRedirect = vi.hoisted(() => vi.fn((to: string) => { throw new Error(`NEXT_REDIRECT ${to}`); }));
const notFound = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_NOT_FOUND"); }));
vi.mock("next/navigation", () => ({ permanentRedirect, notFound }));

import sitemap from "@/app/sitemap";
import StatesIndex from "@/app/state/page";
import ArchiveIndexPage from "@/app/archive/page";
import EntityHubPage, { generateMetadata as entityMetadata } from "@/app/entity/[slug]/page";
import { generateMetadata as subjectMetadata } from "@/app/subject/[...path]/page";
import { metadata as feedLayout } from "@/app/feed/layout";
import { metadata as trendingLayout } from "@/app/trending/layout";

const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });

const HUBS = {
  floor: 20,
  window_days: 30,
  states: [
    { code: "IN-KA", name: "Karnataka", slug: "karnataka", multi_outlet: 327, indexable: true },
    { code: "IN-AS", name: "Assam", slug: "assam", multi_outlet: 16, indexable: false },
    { code: "IN-DL", name: "Delhi", slug: "delhi", multi_outlet: 103, indexable: true },
  ],
};
const reading = (date: string, over: Record<string, unknown> = {}) => ({
  date, read: true, whole_day: true, read_from: `${date}T00:00:00Z`, read_to: `${date}T18:00:00Z`, settled: true, records: 900, multi_outlet: 112, indexable: true, ...over,
});
const ARCHIVE = {
  first_day: "2026-09-03",
  today: "2026-09-29",
  floor: 20,
  days: [
    reading("2026-09-28", { whole_day: false, settled: false, read_from: "2026-09-27T18:30:59Z", read_to: "2026-09-28T02:11:14Z", multi_outlet: 23, indexable: false }),
    reading("2026-09-27"),
    reading("2026-09-26", { multi_outlet: 12, indexable: false }),
    reading("2026-09-25", { read: false, whole_day: false, read_from: null, read_to: null, records: null, multi_outlet: null, indexable: false }),
    reading("2026-09-24", { read: false, whole_day: false, read_from: null, read_to: null, records: null, multi_outlet: null, indexable: false }),
    reading("2026-09-23", { whole_day: false, read_from: "2026-09-23T05:40:00Z", read_to: "2026-09-23T10:31:00Z" }),
  ],
};

let entityFetches = 0;
function stubApi() {
  entityFetches = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.includes("/api/v1/regions/hubs")) return json(HUBS);
    if (url.includes("/api/v1/archive")) return json(ARCHIVE);
    if (url.includes("/api/v1/subjects")) return json({ roots: [], nodes: [{ path: "civic", slug: "civic", label: "Civic & Safety", depth: 1, story_count: 412 }] });
    if (url.includes("/api/v1/subject/")) {
      return json({ node: { path: "civic", slug: "civic", label: "Civic & Safety", depth: 1, story_count: 2852 }, ancestors: [], children: [], story_count: 2852, stories: [] });
    }
    if (url.includes("/api/v1/entity/")) {
      entityFetches += 1;
      return json({ entity: { slug: "dk-shivakumar", name: "DK Shivakumar", entity_type: "person", schema_type: "Person", qid: null, aliases: [] }, record_count: 9, indexable: true, records: [] });
    }
    return json({ items: [], stories: [], nodes: [] });
  }));
}

beforeEach(() => {
  stubApi();
  permanentRedirect.mockClear();
});
afterEach(() => vi.unstubAllGlobals());

const html = async (el: Promise<React.ReactElement>) => new DOMParser().parseFromString(renderToString(await el), "text/html");

describe("the sitemap offers a hub or a day only when it asks to be indexed", () => {
  it("lists both indexes, the indexable hubs and the indexable days, and nothing under a floor", async () => {
    const urls = (await sitemap()).map((e) => new URL(e.url).pathname);
    expect(urls).toEqual(expect.arrayContaining(["/state", "/state/karnataka", "/state/delhi", "/archive", "/feed/2026-09-27", "/feed/2026-09-23"]));
    expect(urls).not.toContain("/state/assam");
    expect(urls).not.toContain("/feed/2026-09-28"); // reading stopped mid-day: not settled
    expect(urls).not.toContain("/feed/2026-09-26"); // under the floor
    expect(urls).not.toContain("/feed/2026-09-25"); // not read
  });

  it("still serves both indexes when the API cannot answer, and no hub or day it cannot vouch for", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("api down"); }));
    const urls = (await sitemap()).map((e) => new URL(e.url).pathname);
    expect(urls).toEqual(expect.arrayContaining(["/state", "/archive"]));
    expect(urls.filter((u) => u.startsWith("/state/") || /^\/feed\/\d/.test(u))).toEqual([]);
  });
});

describe("/state — every hub by name, never ranked", () => {
  it("prints each count, marks and does not follow a hub under the floor", async () => {
    const doc = await html(StatesIndex());
    const link = (name: string) => [...doc.querySelectorAll("a")].find((a) => a.textContent === name)!;
    expect(link("Karnataka").getAttribute("href")).toBe("/state/karnataka");
    expect(link("Karnataka").getAttribute("rel")).toBeNull();
    expect(link("Assam").getAttribute("rel")).toBe("nofollow");
    expect(link("Assam").parentElement?.textContent).toContain("16 records");
    expect(link("Assam").parentElement?.textContent).toContain("fewer than 20 records in 30 days");
    expect(link("Karnataka").parentElement?.textContent).not.toContain("fewer than");
    // States alphabetically (Assam before Karnataka whatever the counts), union territories apart.
    const states = [...doc.querySelectorAll('section[aria-labelledby="states"] a')].map((a) => a.textContent);
    expect(states.indexOf("Assam")).toBeLessThan(states.indexOf("Karnataka"));
    expect(states).not.toContain("Delhi");
    expect([...doc.querySelectorAll('section[aria-labelledby="union-territories"] a')].map((a) => a.textContent)).toContain("Delhi");
  });

  it("prints Not counted yet, never 0, when the counts cannot be read", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("api down"); }));
    const text = (await html(StatesIndex())).body.textContent!;
    expect(text).toContain("Not counted yet");
    expect(text).not.toMatch(/\b0 records/);
  });

  it("lists only the indexable hubs in its structured data", async () => {
    const [collection] = [...(await html(StatesIndex())).querySelectorAll('script[type="application/ld+json"]')].map((s) => JSON.parse(s.textContent!));
    expect(collection["@type"]).toBe("CollectionPage");
    expect(collection.mainEntity.itemListElement.map((i: { name: string }) => i.name)).toEqual(["Delhi", "Karnataka"]);
  });
});

describe("/archive — every day, and the days not read said so", () => {
  it("links each read day, not following one under the floor or unsettled, and folds the days not read into one line", async () => {
    const doc = await html(ArchiveIndexPage());
    const day = (date: string) => doc.querySelector(`a[href="/feed/${date}"]`);
    expect(day("2026-09-27")?.getAttribute("rel")).toBeNull();
    expect(day("2026-09-26")?.getAttribute("rel")).toBe("nofollow");
    expect(day("2026-09-28")?.getAttribute("rel")).toBe("nofollow");
    expect(day("2026-09-25")).toBeNull();
    expect(day("2026-09-24")).toBeNull();
    const text = doc.body.textContent!;
    expect(text).toContain("24 September 2026 – 25 September 2026");
    expect(text).toContain("Prism was not reading");
    expect(text).toContain("stopped at 07:41 IST, not complete");
    expect(text).toContain("read 11:10–16:01 IST");
  });
});

describe("/entity/<a state's name> — the hub replaces it", () => {
  it("308s to the state's hub before asking the API anything", async () => {
    await expect(EntityHubPage({ params: Promise.resolve({ slug: "karnataka" }) })).rejects.toThrow("NEXT_REDIRECT /state/karnataka");
    await expect(entityMetadata({ params: Promise.resolve({ slug: "jammu-and-kashmir" }) })).rejects.toThrow("NEXT_REDIRECT /state/jammu-and-kashmir");
    expect(permanentRedirect).toHaveBeenCalledWith("/state/karnataka");
    expect(entityFetches).toBe(0);
  });

  it("leaves every other actor's page alone", async () => {
    await EntityHubPage({ params: Promise.resolve({ slug: "dk-shivakumar" }) });
    expect(permanentRedirect).not.toHaveBeenCalled();
    expect(entityFetches).toBeGreaterThan(0);
  });
});

describe("titles", () => {
  it("brands the day archive and the story arcs through their layouts' template (P2-3)", () => {
    for (const layout of [feedLayout, trendingLayout]) {
      expect(layout.title).toMatchObject({ template: "%s | Prism" });
      expect((layout.title as { default: string }).default).toBeTruthy();
    }
  });

  it("names a subject page as the archive it lists, and counts its last 30 days (P2-2)", async () => {
    const meta = await subjectMetadata({ params: Promise.resolve({ path: ["civic"] }) });
    expect(meta.title).toBe("Civic & Safety news from Indian outlets — the record");
    expect(meta.title).not.toMatch(/today/i);
    expect(meta.description).toMatch(/^412 stories in the last 30 days in Civic & Safety, from monitored Indian outlets/);
  });
});
