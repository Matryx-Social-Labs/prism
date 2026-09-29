import { beforeEach, describe, expect, it, vi } from "vitest";
import { renderToString } from "react-dom/server";
import type { FeedItem, StateHubPage } from "@/lib/api";

const fetchStateHub = vi.hoisted(() => vi.fn());
const fetchFeed = vi.hoisted(() => vi.fn());
const notFound = vi.hoisted(() => vi.fn(() => { throw new Error("NEXT_NOT_FOUND"); }));
vi.mock("next/navigation", () => ({ notFound }));
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchStateHub, fetchFeed }));

import StateHubRoute, { generateMetadata, generateStaticParams } from "@/app/state/[slug]/page";

const NOINDEX = { index: false, follow: true };
const row = (id: string, indexable: boolean, publishers: string[] = ["a", "b"]) =>
  ({
    id, indexable, title: `Record ${id}`, summary: null, sector: "politics", subsector: null, regions: ["IN-KA"], image_url: null,
    is_regional: true, coverage: null, event_type: null, source_count: publishers.length, cvss_score: null, cvss_severity: null,
    kev_listed: false, cve_ids: [], tickers: [], catalyst: null, price_impact_direction: null, headline_lang: null,
    available_languages: ["en"], last_updated_at: "2026-09-27T10:00:00Z", latest_published_at: "2026-09-27T10:00:00Z", score: 0,
    outlets: publishers.map((p) => ({ slug: p, publisher: p, name: p, code: p.toUpperCase(), origin: "national", language: "en" })),
  }) as FeedItem;

const hub = (over: Partial<StateHubPage> = {}): StateHubPage => ({
  code: "IN-KA", name: "Karnataka", slug: "karnataka", qid: "Q1185", window_days: 30, floor: 20, records: 6325, multi_outlet: 327,
  indexable: true, subjects: [{ root: "politics", count: 130 }, { root: "civic", count: 105 }], languages: ["kn", "en", "ml", "hi"],
  desks: [{ publisher: "prajavani", name: "Prajavani", language: "kn" }, { publisher: "tv9kannada", name: "TV9 Kannada", language: "kn" }],
  speakers: [{ slug: "dk-shivakumar", name: "DK Shivakumar", records: 2, indexable: true }, { slug: "a-stub", name: "A Stub", records: 2, indexable: false }],
  speakers_window: 60, items: [row("m1", true), row("m2", true, ["a", "b", "c"])],
  ...over,
});

const params = (slug: string) => ({ params: Promise.resolve({ slug }) });
const page = async (slug: string) => new DOMParser().parseFromString(renderToString(await StateHubRoute(params(slug))), "text/html");
const ld = (doc: Document) => [...doc.querySelectorAll('script[type="application/ld+json"]')].map((s) => JSON.parse(s.textContent!));

beforeEach(() => {
  fetchStateHub.mockReset().mockResolvedValue(hub());
  fetchFeed.mockReset().mockResolvedValue([row("s1", false, ["a"]), row("m1", true)]);
  notFound.mockClear();
});

describe("/state/<slug> — the floor decides the robots", () => {
  it("prerenders the 33 hubs by slug", () => {
    const slugs = generateStaticParams().map((p) => p.slug);
    expect(slugs).toHaveLength(33);
    expect(slugs).toContain("jammu-and-kashmir");
  });

  it("asks to be indexed at or over the floor: the robots key is absent, not undefined", async () => {
    const meta = await generateMetadata(params("karnataka"));
    expect("robots" in meta).toBe(false);
    expect(meta.title).toBe("Karnataka news: one record per story");
    expect(meta.alternates?.canonical).toBe("/state/karnataka");
    expect(meta.description).toBe("Stories placed in Karnataka from monitored Indian outlets, in Kannada, English, Malayalam and 1 more language: who reported each, who said what.");
    expect(fetchStateHub).toHaveBeenCalledWith("IN-KA", 600);
  });

  it("asks not to be indexed under the floor", async () => {
    fetchStateHub.mockResolvedValue(hub({ code: "IN-AS", name: "Assam", slug: "assam", multi_outlet: 16, indexable: false }));
    expect((await generateMetadata(params("assam"))).robots).toEqual(NOINDEX);
  });

  it("asks not to be indexed when the counts could not be read, rather than guess", async () => {
    fetchStateHub.mockRejectedValue(new Error("api down"));
    expect((await generateMetadata(params("karnataka"))).robots).toEqual(NOINDEX);
  });

  it("is a 404 for a slug that names no state", async () => {
    await expect(StateHubRoute(params("bengaluru"))).rejects.toThrow("NEXT_NOT_FOUND");
  });
});

describe("/state/<slug> — counts, denominator and line form", () => {
  it("prints the count, the languages and the outlets with a desk there as the denominator", async () => {
    const doc = await page("karnataka");
    expect(doc.querySelector("h1")?.textContent).toBe("Karnataka");
    expect(doc.body.textContent).toContain("327 records from two or more outlets");
    expect(doc.body.textContent).toContain("Reports in Kannada, English, Malayalam and 1 more language.");
    const desks = [...doc.querySelectorAll('a[href="/sources"]')].find((a) => a.textContent?.includes("desk"));
    expect(desks?.textContent).toBe("2 outlets with a desk in Karnataka");
    expect(desks?.parentElement?.textContent).toContain("Prajavani · TV9 Kannada");
  });

  it("says so when no outlet Prism reads has a desk in the state", async () => {
    fetchStateHub.mockResolvedValue(hub({ code: "IN-GJ", name: "Gujarat", slug: "gujarat", desks: [] }));
    expect((await page("gujarat")).body.textContent).toContain("No outlet Prism reads has a desk in Gujarat yet");
  });

  it("prints — and Not counted yet when the API cannot answer, never 0", async () => {
    fetchStateHub.mockRejectedValue(new Error("api down"));
    const text = (await page("karnataka")).body.textContent!;
    expect(text).toContain("Not counted yet");
    expect(text).not.toMatch(/\b0 records/);
  });

  it("links subjects to their pages with counts, not to a topic × state page", async () => {
    const doc = await page("karnataka");
    const chips = [...doc.querySelectorAll('nav[aria-label="Subjects in Karnataka"] a')].map((a) => [a.getAttribute("href"), a.textContent]);
    expect(chips).toEqual([["/sector/politics", "Politics 130"], ["/subject/civic", "Civic & Safety 105"]]);
  });

  it("lists records from two or more outlets most outlets first, and one-source rows dashed and not followed", async () => {
    const doc = await page("karnataka");
    const multi = doc.querySelector('section[aria-labelledby="state-multi"]')!;
    expect([...multi.querySelectorAll("a.p-row")].map((a) => a.getAttribute("href"))).toEqual(["/story/m1", "/story/m2"]);
    const single = doc.querySelector('section[aria-labelledby="state-single"]')!;
    expect(single.className).toContain("[border-top-style:dashed]");
    const one = single.querySelector("a.p-row")!;
    expect(one.getAttribute("href")).toBe("/story/s1");
    expect(one.getAttribute("rel")).toBe("nofollow");
  });

  it("links who is quoted, not following a stub", async () => {
    const doc = await page("karnataka");
    const quoted = [...doc.querySelectorAll('section[aria-labelledby="quoted-here"] a')].map((a) => [a.getAttribute("href"), a.getAttribute("rel")]);
    expect(quoted).toEqual([["/entity/dk-shivakumar", null], ["/entity/a-stub", "nofollow"]]);
  });
});

describe("/state/<slug> — structured data", () => {
  it("is a CollectionPage about the AdministrativeArea, listing its records, with a breadcrumb", async () => {
    const [collection, crumbs] = ld(await page("karnataka"));
    expect(collection).toMatchObject({
      "@context": "https://schema.org",
      "@type": "CollectionPage",
      about: { "@type": "AdministrativeArea", name: "Karnataka", identifier: "IN-KA", sameAs: ["https://www.wikidata.org/wiki/Q1185"] },
      mainEntity: { "@type": "ItemList", numberOfItems: 2 },
    });
    expect(collection.url).toMatch(/\/state\/karnataka$/);
    expect(collection.mainEntity["@context"]).toBeUndefined();
    expect(collection.mainEntity.itemListElement.map((i: { url: string }) => i.url.split("/story/")[1])).toEqual(["m1", "m2"]);
    expect(crumbs["@type"]).toBe("BreadcrumbList");
    expect(crumbs.itemListElement.map((i: { name: string }) => i.name)).toEqual(["Prism", "States", "Karnataka"]);
  });

  it("claims no Wikidata item it does not know", async () => {
    fetchStateHub.mockResolvedValue(hub({ qid: null }));
    const [collection] = ld(await page("karnataka"));
    expect(collection.about.sameAs).toBeUndefined();
  });
});
