import type { ReactElement } from "react";
import { render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

// The share cards as the routes build them (audit 06 §2.4 I1–I4). ImageResponse
// is swapped for a holder of the element it was given, so the card's words can
// be read in the DOM; Satori itself is not under test.
vi.mock("next/og", () => ({
  ImageResponse: class {
    constructor(public element: ReactElement, public init: unknown) {}
  },
}));
vi.mock("@/lib/ogFonts", async () => ({ ...(await vi.importActual<typeof import("@/lib/ogFonts")>("@/lib/ogFonts")), ogFonts: async () => [] }));
const fetchEvent = vi.hoisted(() => vi.fn());
const fetchSources = vi.hoisted(() => vi.fn());
const fetchTrendingStory = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchEvent, fetchSources, fetchTrendingStory }));

import * as siteRoute from "@/app/opengraph-image";
import * as storyRoute from "@/app/story/[id]/opengraph-image";
import * as quoteRoute from "@/app/story/[id]/quote/[n]/opengraph-image";
import * as trendingRoute from "@/app/trending/[slug]/opengraph-image";
import { SITE_HEADLINE, SITE_LINE, SiteCard } from "@/lib/ogCard";

type Held = { element: ReactElement };
const cardText = async (res: unknown) => render((await res as Held).element).container.textContent ?? "";

const report = (id: string, publisher: string, language: string, origin = "national") => ({
  article_id: id, source_name: publisher, source_slug: publisher, publisher, origin, language,
  url: `https://x.example/${id}`, title: `T ${id}`, published_at: "2026-09-27T10:00:00Z", funding: null,
});

const record = (over: Record<string, unknown> = {}) => ({
  id: "e1", title: "The council widens the ring road", summary: null, sector: "politics", story_slug: null,
  last_updated_at: "2026-09-27T12:00:00Z", monitored_outlets: 42,
  sources: [report("a1", "thehindu", "en"), report("a2", "prajavani", "kn", "regional"), report("a3", "reuters", "en", "wire")],
  ...over,
});

const storyCard = () => storyRoute.default({ params: Promise.resolve({ id: "e1" }) });

beforeEach(() => {
  fetchEvent.mockReset();
  fetchSources.mockReset().mockResolvedValue({ outlets: 40, checked_at: null, feeds: [] });
  fetchTrendingStory.mockReset().mockResolvedValue(null);
});

describe("the record's share card counts out of the monitored set", () => {
  it("prints k of n monitored outlets with the record's own denominator, as its header does", async () => {
    fetchEvent.mockResolvedValue(record());
    const text = await cardText(storyCard());
    expect(text).toContain("3 of 42 monitored outlets · 2 languages");
    expect(fetchSources).not.toHaveBeenCalled();
  });

  it("reads the public list's size for an older payload without one", async () => {
    fetchEvent.mockResolvedValue(record({ monitored_outlets: undefined }));
    expect(await cardText(storyCard())).toContain("3 of 40 monitored outlets · 2 languages");
  });

  it("says one of n for a single source", async () => {
    fetchEvent.mockResolvedValue(record({ sources: [report("a1", "thehindu", "en")] }));
    expect(await cardText(storyCard())).toContain("1 of 42 monitored outlets · the record grows as others report");
  });

  // I4: "· ML" wrapped onto a line of its own on a four-language record.
  it("names a lone language on the mono line and leaves several to the count line", async () => {
    fetchEvent.mockResolvedValue(record());
    expect(await cardText(storyCard())).not.toMatch(/· (EN|KN)\b/);
    fetchEvent.mockResolvedValue(record({ sources: [report("a1", "prajavani", "kn"), report("a2", "vk", "kn")] }));
    expect(await cardText(storyCard())).toMatch(/UPDATED 27 SEPT 15:30 IST · KN/);
  });
});

describe("the developing story's share card", () => {
  it("counts its outlets out of the public list", async () => {
    const outlet = (publisher: string) => ({ outlet: { publisher, origin: "national", language: "en" }, reports: 1 });
    fetchTrendingStory.mockResolvedValue({
      slug: "ring-road", label: "The ring road", sector: "politics", boundary_status: "provisional",
      outlets: [outlet("thehindu"), outlet("deccanherald")],
      developments: [{ id: "d1", occurred_at: "2026-09-26T00:00:00Z" }, { id: "d2", occurred_at: "2026-09-27T00:00:00Z" }],
    });
    expect(await cardText(trendingRoute.default({ params: Promise.resolve({ slug: "ring-road" }) }))).toContain("2 records · 2 of 40 monitored outlets");
  });
});

describe("the brand card", () => {
  // DESIGN.md: a coverage bar is always printed with its count. The brand card
  // is prerendered, so it has no count to print, and so no bar.
  it("draws no coverage bar", () => {
    const { container } = render(<SiteCard headline={SITE_HEADLINE} line={SITE_LINE} />);
    expect(container.querySelectorAll('[style*="flex-grow"]')).toHaveLength(0);
  });

  it("says what the landing says: one page per story, word for word, who covered it, free", () => {
    expect(SITE_LINE).toMatch(/^One page per story from the outlets Prism monitors/);
    expect(SITE_LINE).toMatch(/word for word/);
    expect(SITE_LINE).toMatch(/Free to read\.$/);
  });
});

describe("og:image:alt", () => {
  it("every card route describes its card", () => {
    for (const route of [siteRoute, storyRoute, quoteRoute, trendingRoute]) expect(route.alt.length).toBeGreaterThan(40);
    // The brand card's alt is exactly its words.
    expect(siteRoute.alt).toBe(`readPrism.news: ${SITE_HEADLINE} ${SITE_LINE}`);
    expect(storyRoute.alt).toMatch(/outlets Prism monitors/);
    expect(quoteRoute.alt).toMatch(/checked against the article/);
  });
});
