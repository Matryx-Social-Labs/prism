import { afterEach, describe, expect, it, vi } from "vitest";

import { metadata as pulseMetadata } from "@/app/pulse/layout";
import sitemap from "@/app/sitemap";
import { GET as newsSitemap } from "@/app/news-sitemap.xml/route";
import { generateMetadata as quoteMetadata } from "@/app/story/[id]/quote/[n]/page";
import { generateMetadata as storyMetadata } from "@/app/story/[id]/page";
import SubjectPageRoute, { generateMetadata as subjectMetadata } from "@/app/subject/[...path]/page";
import { generateMetadata as entityMetadata } from "@/app/entity/[slug]/page";
import { generateMetadata as arcMetadata } from "@/app/trending/[slug]/page";
import { renderToString } from "react-dom/server";

// What Search Console reported (2026-09-21: 4 of 36 pages indexed, 29 "crawled -
// currently not indexed") and the crawl of our own sitemaps found (2026-09-27,
// tools/seo_crawl_audit.py): the signals below were telling Google to skip us.

const node = (path: string, story_count = 5) => ({ path, slug: path.split(".").pop()!, label: path, depth: path.split(".").length, story_count });
const json = (body: unknown) => new Response(JSON.stringify(body), { status: 200, headers: { "content-type": "application/json" } });

const record = (id: string, indexable: boolean) => ({
  id, title: `Record ${id}`, summary: "s", sector: "politics", lens_briefs: {}, entities: [], sources: [], indexable,
  last_updated_at: new Date().toISOString(), latest_published_at: new Date().toISOString(),
  claims: [{ speaker: "A Speaker", role: null, claims: [{ quote_text: "We will cooperate.", source_name: "The Hindu" }] }],
});
const dev = (id: string) => ({ id, title: `Development ${id}`, first_published_at: new Date().toISOString() });
// Two developments from two outlets unless it is the thin one: a one-record story is a thin page, verified or not.
const story = (slug: string, boundary_status: string) => ({
  slug, canonical_slug: slug, label: `Story ${slug}`, boundary_status, last_updated_at: new Date().toISOString(),
  developments: slug === "thin" ? [dev("a")] : [dev("a"), dev("b")], source_count: slug === "thin" ? 1 : 2,
});

function stubApi() {
  vi.stubGlobal("fetch", vi.fn(async (url: string) => {
    if (url.includes("/api/v1/subjects")) return json({ nodes: [node("business"), node("business.markets"), node("civic"), node("education")] });
    // The API applies the indexable rule and the 48-hour bound (tests/test_site_architecture.py).
    if (url.includes("/api/v1/sitemap/news")) return json({ records: [{ id: "multi", title: "Record multi", published_at: new Date().toISOString() }] });
    if (url.includes("/api/v1/subject/")) {
      const path = decodeURIComponent(url.split("/api/v1/subject/")[1]).split("/").join(".");
      const ancestors = path.split(".").slice(0, -1).map((_, i, all) => node(all.slice(0, i + 1).join(".")));
      return json({ node: node(path), ancestors, children: [], story_count: 5, stories: [] });
    }
    if (url.includes("/api/v1/entity/")) {
      return json({ entity: { slug: "indexable-actor", name: "An Actor", entity_type: "person", schema_type: "Person", qid: null, aliases: [] }, record_count: 9, indexable: true, records: [] });
    }
    const one = url.match(/\/api\/v1\/events\/([^/?]+)$/);
    if (one) return json(record(one[1], one[1] === "multi"));
    const arc = url.match(/\/api\/v1\/trending\/([^/?]+)$/);
    if (arc) return json(story(arc[1], arc[1] === "provisional" ? "provisional" : "verified"));
    if (url.includes("/api/v1/trending")) return json({ stories: [story("provisional", "provisional"), story("verified", "verified")] });
    return json({ items: [record("single", false), record("multi", true)] });
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

// Search Console, 2026-09-21: of 29 pages crawled and not indexed, 13 records
// came from ONE outlet (a rewrite Google already has from that outlet) and 4
// stories were provisional groupings whose URL named one event and whose page
// showed another. Neither asks to be indexed now, and neither is offered in a
// sitemap; both stay readable and linked (follow).
const NOINDEX = { index: false, follow: true };

describe("records and stories that should not be indexed say so", () => {
  it("a one-outlet record, and a quote from it, ask not to be indexed", async () => {
    stubApi();
    expect((await storyMetadata({ params: Promise.resolve({ id: "single" }) })).robots).toEqual(NOINDEX);
    expect((await quoteMetadata({ params: Promise.resolve({ id: "single", n: "0-0" }) })).robots).toEqual(NOINDEX);
  });

  // The KEY must be absent, not undefined: Next does not fall back to the
  // layout's robots for an explicit undefined — it erases them, and with them
  // max-image-preview:large and max-snippet (live on every indexable record,
  // entity and subject page until 2026-09-27).
  it("a record from two outlets keeps the site's default robots", async () => {
    stubApi();
    expect("robots" in (await storyMetadata({ params: Promise.resolve({ id: "multi" }) }))).toBe(false);
    expect("robots" in (await quoteMetadata({ params: Promise.resolve({ id: "multi", n: "0-0" }) }))).toBe(false);
  });

  it("an actor page worth indexing and a subject with stories keep the site's default robots", async () => {
    stubApi();
    expect("robots" in (await entityMetadata({ params: Promise.resolve({ slug: "indexable-actor" }) }))).toBe(false);
    expect("robots" in (await subjectMetadata({ params: Promise.resolve({ path: ["civic"] }) }))).toBe(false);
  });

  it("a provisional story asks not to be indexed; a verified one does not", async () => {
    stubApi();
    expect((await arcMetadata({ params: Promise.resolve({ slug: "provisional" }) })).robots).toEqual(NOINDEX);
    expect("robots" in (await arcMetadata({ params: Promise.resolve({ slug: "verified" }) }))).toBe(false);
    expect((await arcMetadata({ params: Promise.resolve({ slug: "thin" }) })).robots).toEqual(NOINDEX);
  });

  it("the sitemap and the news sitemap offer only what asks to be indexed", async () => {
    stubApi();
    const urls = (await sitemap()).map((e) => new URL(e.url).pathname);
    expect(urls).toContain("/story/multi");
    expect(urls).not.toContain("/story/single");
    expect(urls).toContain("/trending/verified");
    expect(urls).not.toContain("/trending/provisional");
    const news = await (await newsSitemap()).text();
    expect(news).toContain("/story/multi");
    expect(news).not.toContain("/story/single");
  });

  // Review 2026-09-29: a feed can stamp a report in the future; the record's
  // lastmod must never pass its own rebuild (the API's sitemaps clamp the same).
  it("never dates a record after its own last rebuild", async () => {
    const rebuilt = "2026-09-28T02:11:00+00:00";
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      if (url.includes("/api/v1/feed")) return json({ items: [{ ...record("multi", true), last_updated_at: rebuilt, latest_published_at: "2031-01-01T00:00:00+00:00" }] });
      return json({ nodes: [], stories: [] });
    }));
    const entry = (await sitemap()).find((e) => e.url.endsWith("/story/multi"));
    expect(entry?.lastModified).toBe(rebuilt);
  });

  it("the news sitemap is a 503 to come back to when the API is down, never an empty file", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new Error("api down"); }));
    const res = await newsSitemap();
    expect(res.status).toBe(503);
    expect(res.headers.get("Retry-After")).toBe("300");
  });
});
