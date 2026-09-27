import { afterEach, describe, expect, it, vi } from "vitest";

import { metadata as pulseMetadata } from "@/app/pulse/layout";
import sitemap from "@/app/sitemap";
import SubjectPageRoute, { generateMetadata as subjectMetadata } from "@/app/subject/[...path]/page";
import { renderToString } from "react-dom/server";

// What Search Console reported (2026-09-21: 4 of 36 pages indexed, 29 "crawled -
// currently not indexed") and the crawl of our own sitemaps found (2026-09-27,
// tools/seo_crawl_audit.py): the signals below were telling Google to skip us.

const node = (path: string, story_count = 5) => ({ path, slug: path.split(".").pop()!, label: path, depth: path.split(".").length, story_count });
const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });

function stubApi() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.includes("/api/v1/subjects")) return json({ nodes: [node("business"), node("business.markets"), node("civic"), node("education")] });
    if (url.includes("/api/v1/subject/")) {
      const path = decodeURIComponent(url.split("/api/v1/subject/")[1]).split("/").join(".");
      const ancestors = path.split(".").slice(0, -1).map((_, i, all) => node(all.slice(0, i + 1).join(".")));
      return json({ node: node(path), ancestors, children: [], story_count: 5, stories: [] });
    }
    if (url.includes("/api/v1/trending")) return json({ stories: [] });
    return json({ items: [] });
  }));
}

afterEach(() => vi.unstubAllGlobals());

describe("pages that duplicate another are not offered as originals", () => {
  // Every record on /subject/business is on /sector/business, under the same
  // title — so Google indexes one and drops the other. The sector page is the
  // one to keep; Education and Civic have no sector page, and deeper subject
  // nodes are lists of their own.
  it.each([
    [["business"], "/sector/business"],
    [["business", "markets"], "/subject/business/markets"],
    [["civic"], "/subject/civic"],
  ])("/subject/%s names %s as its original", async (path, canonical) => {
    stubApi();
    const meta = await subjectMetadata({ params: Promise.resolve({ path }) });
    expect(meta.alternates?.canonical).toBe(canonical);
  });

  it.each([
    [["business"], "the page itself"],
    [["business", "markets"], "a deeper page's breadcrumb"],
  ])("structured data on /subject/%s names the sector page, as %s", async (path) => {
    stubApi();
    const html = renderToString(await SubjectPageRoute({ params: Promise.resolve({ path }) }));
    const ld = [...html.matchAll(/<script type="application\/ld\+json">(.*?)<\/script>/g)].map((m) => m[1]).join(" ");
    expect(ld).toContain("/sector/business");
    expect(ld).not.toMatch(/\/subject\/business"/);
  });

  it("the sitemap lists a subject only where no sector page has the same records, and never /pulse", async () => {
    stubApi();
    const urls = (await sitemap()).map((e) => new URL(e.url).pathname);
    expect(urls).toContain("/sector/business");
    expect(urls).toContain("/subject/business/markets");
    expect(urls).toContain("/subject/civic");
    expect(urls).not.toContain("/subject/business");
    // Market Pulse renders in the browser: a crawler gets 26 words.
    expect(urls).not.toContain("/pulse");
  });
});

describe("a page with nothing in its HTML asks not to be indexed", () => {
  it("/pulse, until it renders on the server", () => {
    expect(pulseMetadata.robots).toEqual({ index: false, follow: true });
  });
});
