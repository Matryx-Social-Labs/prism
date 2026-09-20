import { describe, expect, it } from "vitest";
import robots from "@/app/robots";
import type { EventDetail, TrendingStoryDetail } from "@/lib/api";
import { itemListLd, jsonLd, newsArticleLd, siteGraph, storyLd } from "@/lib/seo";

const event = {
  id: "e1",
  title: "A headline with </script> in it",
  summary: "Two people died after an electric shock near a pandal.",
  sector: "politics",
  occurred_at: "2026-09-20T10:00:00Z",
  last_updated_at: "2026-09-20T12:00:00Z",
  lens_briefs: {},
  entities: [{ name: "Lalbaug", entity_type: "place", role: "location" }, { name: "Mumbai Police", entity_type: "org", role: "actor" }],
  sources: [
    { article_id: "a1", source_name: "Amar Ujala", source_slug: "amar-ujala", publisher: "Amar Ujala", language: "hi", url: "https://example.com/a1", title: "Report one", published_at: "2026-09-20T09:00:00Z", stance: null, funding: null },
    { article_id: "a2", source_name: "No link", source_slug: "x", url: null, title: "Unlinked", published_at: null, stance: null, funding: null },
  ],
  image_url: "https://publisher.example/photo.jpg",
} as unknown as EventDetail;

describe("structured data", () => {
  it("a record is a NewsArticle grounded in the reports it is based on, with no publisher photograph", () => {
    const ld = newsArticleLd(event) as Record<string, unknown>;
    expect(ld["@type"]).toBe("NewsArticle");
    expect(ld.url).toMatch(/\/story\/e1$/);
    expect(ld.isBasedOn).toEqual([
      expect.objectContaining({ url: "https://example.com/a1", headline: "Report one", inLanguage: "hi", publisher: { "@type": "Organization", name: "Amar Ujala" } }),
    ]);
    expect(ld.about).toEqual([{ "@type": "Thing", name: "Lalbaug" }, { "@type": "Thing", name: "Mumbai Police" }]);
    expect(ld.isAccessibleForFree).toBe(true);
    expect(ld).not.toHaveProperty("image");
    expect(ld.publisher).toEqual({ "@id": expect.stringMatching(/#organization$/) });
  });

  it("serialising never lets a scraped headline close the script element", () => {
    const out = jsonLd(newsArticleLd(event));
    expect(out).not.toContain("</script>");
    expect(out).toContain("\\u003c/script>");
  });

  it("a story arc lists its developments as parts, oldest first, dated from them", () => {
    const s = {
      canonical_slug: "sir-notices",
      label: "SIR notices",
      sector: "politics",
      source_count: 9,
      cast: ["Election Commission"],
      developments: [
        { id: "d2", title: "Second", occurred_at: "2026-09-19T00:00:00Z", sector: null, image_url: null, is_current: true, why: null },
        { id: "d1", title: "First", occurred_at: "2026-09-17T00:00:00Z", sector: null, image_url: null, is_current: false, why: null },
      ],
    } as unknown as TrendingStoryDetail;
    const ld = storyLd(s) as Record<string, unknown>;
    expect(ld.datePublished).toBe("2026-09-17T00:00:00Z");
    expect(ld.dateModified).toBe("2026-09-19T00:00:00Z");
    expect((ld.hasPart as { url: string }[]).map((p) => p.url)).toEqual([expect.stringMatching(/\/story\/d1$/), expect.stringMatching(/\/story\/d2$/)]);
  });

  it("the list of the day is an ItemList with positions; the site graph names the publisher and how to search", () => {
    const ld = itemListLd("Today", "https://x.test/feed", [{ url: "https://x.test/story/1", name: "One" }, { url: "https://x.test/story/2", name: "Two" }]);
    expect(ld.numberOfItems).toBe(2);
    expect(ld.itemListElement[1]).toEqual({ "@type": "ListItem", position: 2, url: "https://x.test/story/2", name: "Two" });
    const g = siteGraph()["@graph"] as Record<string, unknown>[];
    expect(g[0]).toMatchObject({ "@type": "NewsMediaOrganization", name: "Prism", legalName: "Prism Media Intelligence LLP" });
    expect((g[1].potentialAction as { target: { urlTemplate: string } }).target.urlTemplate).toMatch(/\/search\?q=\{search_term_string\}$/);
  });
});

describe("robots", () => {
  it("keeps the record open to every crawler and closes the account, search and the labelling tool", () => {
    const r = robots();
    const rule = Array.isArray(r.rules) ? r.rules[0] : r.rules;
    expect(rule.userAgent).toBe("*");
    expect(rule.allow).toBe("/");
    for (const p of ["/account", "/search", "/label/", "/you", "/plus/welcome"]) expect(rule.disallow).toContain(p);
    expect(r.sitemap).toEqual([expect.stringMatching(/\/sitemap\.xml$/), expect.stringMatching(/\/news-sitemap\.xml$/)]);
  });
});
