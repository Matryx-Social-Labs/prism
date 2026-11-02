import { beforeEach, expect, it, vi } from "vitest";
import type { TrendingStoryDetail } from "@/lib/api";

const fetchTrendingStory = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ notFound: vi.fn(), redirect: vi.fn() }));
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchTrendingStory }));

import { generateMetadata } from "@/app/trending/[slug]/page";

// A story is labelled with its lead record's headline. Titled with the label
// alone, the story and that record were two pages with one title: 25 of 25
// duplicate titles in the crawl of 2026-11-02, the kind of pair Google keeps one
// of. The share card keeps the bare label.
const story = {
  slug: "s", canonical_slug: "s", label: "Sebi urges government to scrap long-term capital gains tax",
  boundary_status: "verified", source_count: 13, developments: [{ title: "Sebi urges government to scrap long-term capital gains tax" }, { title: "Sitharaman signals a review" }],
} as unknown as TrendingStoryDetail;

beforeEach(() => fetchTrendingStory.mockReset().mockResolvedValue(story));

it("titles a story apart from the record it is labelled after", async () => {
  const meta = await generateMetadata({ params: Promise.resolve({ slug: "s" }) });
  expect(meta.title).toBe(`${story.label}: the story so far`);
  expect(meta.title).not.toBe(story.developments[0].title);
  expect(meta.openGraph?.title).toBe(story.label);
});
