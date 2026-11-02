// @vitest-environment node
import { afterEach, describe, expect, it, vi } from "vitest";
import { SITE_URL } from "@/lib/site";
import { GET } from "./route";
import { GET as month } from "../records-sitemap/[file]/route";

afterEach(() => vi.unstubAllGlobals());

const file = (name: string) => month(new Request(`${SITE_URL}/records-sitemap/${name}`), { params: Promise.resolve({ file: name }) });

// One file stopped at the protocol's 50,000 URLs; October alone added 15,257
// indexable records, so the oldest would have fallen out within two months
// (2026-11-02). records-sitemap.xml keeps its submitted address as an index.
describe("records-sitemap.xml", () => {
  it("is an index of one file per month, each with its newest lastmod", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Response.json({ months: [
      { month: "2026-10", records: 2, lastmod: "2026-10-31T08:00:00+00:00" },
      { month: "2026-09", records: 1, lastmod: null },
    ] })));
    const xml = await (await GET()).text();
    expect(xml).toContain("<sitemapindex");
    expect(xml).toContain(`<sitemap><loc>${SITE_URL}/records-sitemap/2026-10.xml</loc><lastmod>2026-10-31T08:00:00+00:00</lastmod></sitemap>`);
    expect(xml).toContain(`<sitemap><loc>${SITE_URL}/records-sitemap/2026-09.xml</loc></sitemap>`);
  });

  it("is a 503 with Retry-After when the API cannot answer, never an empty index", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response("x", { status: 500 })));
    const res = await GET();
    expect(res.status).toBe(503);
    expect(res.headers.get("Retry-After")).toBeTruthy();
  });
});

describe("records-sitemap/<month>.xml", () => {
  it("lists that month's records with their content lastmod", async () => {
    const f = vi.fn(async (url: string) => url && Response.json({ records: [{ id: "e1", lastmod: "2026-10-20T08:00:00+00:00" }, { id: "e3", lastmod: null }] }));
    vi.stubGlobal("fetch", f);
    const xml = await (await file("2026-10.xml")).text();
    expect(String(f.mock.calls[0][0])).toContain("/api/v1/sitemap/records?month=2026-10");
    expect(xml).toContain(`<url><loc>${SITE_URL}/story/e1</loc><lastmod>2026-10-20T08:00:00+00:00</lastmod></url>`);
    expect(xml).toContain(`<url><loc>${SITE_URL}/story/e3</loc></url>`);
  });

  it("is a 404 for anything but a month's file, without asking the API", async () => {
    const f = vi.fn();
    vi.stubGlobal("fetch", f);
    for (const name of ["2026-13.xml", "2026-10", "../x.xml", "2026-10.xml.gz"]) expect((await file(name)).status).toBe(404);
    expect(f).not.toHaveBeenCalled();
  });
});
