import { afterEach, describe, expect, it, vi } from "vitest";

import { GET } from "@/app/feed.xml/route";
import { atomFeed, type AtomRecord } from "@/lib/atom";
import { SITE_URL } from "@/lib/site";

const ATOM = "http://www.w3.org/2005/Atom";
const rec = (id: string, over: Partial<AtomRecord> = {}): AtomRecord => ({ id, title: `Record ${id}`, summary: "What happened.", updated: "2026-09-28T01:43:00+00:00", ...over });
const parse = (xml: string) => {
  const doc = new DOMParser().parseFromString(xml, "application/xml");
  expect(doc.getElementsByTagName("parsererror")).toHaveLength(0);
  return doc;
};
const text = (el: Element | Document, tag: string) => el.getElementsByTagNameNS(ATOM, tag)[0]?.textContent ?? null;

describe("atomFeed — the Atom document for /feed.xml", () => {
  it("is a well-formed Atom feed: one entry per record, linking the record, dated by its newest report, by Prism", () => {
    const doc = parse(atomFeed([rec("a1", { updated: "2026-09-28T02:00:00+00:00" }), rec("b2")]));
    const feed = doc.documentElement;
    expect(feed.namespaceURI).toBe(ATOM);
    expect(feed.localName).toBe("feed");
    expect(text(feed, "id")).toBe(`${SITE_URL}/feed.xml`);
    expect(text(feed, "updated")).toBe("2026-09-28T02:00:00.000Z");
    const self = [...feed.getElementsByTagNameNS(ATOM, "link")].find((l) => l.getAttribute("rel") === "self");
    expect(self?.getAttribute("href")).toBe(`${SITE_URL}/feed.xml`);
    const entries = [...doc.getElementsByTagNameNS(ATOM, "entry")];
    expect(entries).toHaveLength(2);
    const [first] = entries;
    expect(text(first, "id")).toBe(`${SITE_URL}/story/a1`);
    expect(first.getElementsByTagNameNS(ATOM, "link")[0].getAttribute("href")).toBe(`${SITE_URL}/story/a1`);
    expect(text(first, "title")).toBe("Record a1");
    expect(text(first, "updated")).toBe("2026-09-28T02:00:00.000Z");
    expect(text(first, "summary")).toBe("What happened.");
    expect(text(first.getElementsByTagNameNS(ATOM, "author")[0], "name")).toBe("Prism");
  });

  it("escapes what a headline can carry, and drops the bytes XML refuses", () => {
    const title = `Tata & Sons <"quoted"> 'said'\u0001 — ಕನ್ನಡ`;
    const xml = atomFeed([rec("x", { title, summary: "A < B & C" })]);
    const entry = parse(xml).getElementsByTagNameNS(ATOM, "entry")[0];
    expect(text(entry, "title")).toBe(`Tata & Sons <"quoted"> 'said' — ಕನ್ನಡ`);
    expect(text(entry, "summary")).toBe("A < B & C");
    expect(xml).not.toContain("<\"quoted\">");
  });

  it("leaves out a summary it does not have, and a record with no usable time", () => {
    const doc = parse(atomFeed([rec("s", { summary: null }), rec("t", { updated: "not a time" })]));
    const entries = [...doc.getElementsByTagNameNS(ATOM, "entry")];
    expect(entries.map((e) => text(e, "id"))).toEqual([`${SITE_URL}/story/s`]);
    expect(entries[0].getElementsByTagNameNS(ATOM, "summary")).toHaveLength(0);
  });

  it("is still a valid feed with no records", () => {
    const doc = parse(atomFeed([]));
    expect(doc.getElementsByTagNameNS(ATOM, "entry")).toHaveLength(0);
    expect(Number.isFinite(Date.parse(text(doc, "updated") ?? ""))).toBe(true);
  });
});

describe("GET /feed.xml", () => {
  afterEach(() => vi.unstubAllGlobals());

  it("serves the API's records as Atom, cached at the edge", async () => {
    const fetchMock = vi.fn(async () => new Response(JSON.stringify({ records: [rec("r1")] }), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const res = await GET();
    expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining("/api/v1/sitemap/atom"), expect.anything());
    expect(res.status).toBe(200);
    expect(res.headers.get("Content-Type")).toBe("application/atom+xml; charset=utf-8");
    expect(res.headers.get("Cache-Control")).toContain("s-maxage=");
    expect(await res.text()).toContain(`<id>${SITE_URL}/story/r1</id>`);
  });

  it("is a 503 with Retry-After when the API is down, never an empty feed", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("down", { status: 502 })));
    const res = await GET();
    expect(res.status).toBe(503);
    expect(res.headers.get("Retry-After")).toBe("300");
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("unreachable"); }));
    expect((await GET()).status).toBe(503);
  });
});
