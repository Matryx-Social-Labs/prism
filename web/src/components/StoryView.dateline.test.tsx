/**
 * The record prints when it was first reported (audit 01 P1-2, 06 E9): the same
 * instant its NewsArticle JSON-LD publishes as datePublished, so the visible
 * date and the structured one cannot disagree. Absolute, on the IST clock.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { StoryView } from "@/components/StoryView";
import type { EventDetail } from "@/lib/api";
import { newsArticleLd } from "@/lib/seo";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []) };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [{ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }],
  lensMeta: () => ({ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }),
}));

const SRC = (id: string, publisher: string, published_at: string | null) => ({
  article_id: id, source_name: publisher, source_slug: publisher, publisher, code: "X", origin: "national", language: "en",
  url: `https://x.example/${id}`, title: `T ${id}`, published_at, funding: null,
});

const event = (sources: ReturnType<typeof SRC>[]) => ({
  id: "e1", title: "A story", summary: "S", sector: "news", subsector: null, image_url: null,
  regions: [], occurred_at: "2026-09-27T00:00:00Z", last_updated_at: "2026-09-28T09:00:00Z",
  projection: {}, lens_briefs: { reader: "brief" }, lens_points: {}, available_lenses: ["reader"],
  coverage: null, entities: [], perspectives: [], impacts: [], sources,
}) as unknown as EventDetail;

beforeEach(() => localStorage.clear());

describe("the record's first-reported time", () => {
  it("prints the earliest report's time in IST, the instant the JSON-LD publishes", () => {
    // Listed newest first, as the API does: the earliest is not the first row.
    const e = event([SRC("a2", "thehindu", "2026-09-28T04:10:00Z"), SRC("a1", "reuters", "2026-09-27T20:45:00Z"), SRC("a3", "mint", null)]);
    render(<StoryView event={e} />);
    const line = screen.getByText("First reported 28 Sept, 02:15 IST");
    expect(line).toHaveClass("p-meta__prov"); // the mono provenance voice
    expect(newsArticleLd(e).datePublished).toBe("2026-09-27T20:45:00Z");
  });

  it("takes the API's first_published_at over a report dated outside the record's window", () => {
    // A live blog carrying the date of its first post, months back: the API's
    // window drops it, the bare minimum over the sources did not.
    const e = { ...event([SRC("a1", "reuters", "2026-06-02T10:00:00Z"), SRC("a2", "thehindu", "2026-09-27T20:45:00Z")]),
      first_published_at: "2026-09-27T20:45:00Z" } as EventDetail;
    render(<StoryView event={e} />);
    expect(screen.getByText("First reported 28 Sept, 02:15 IST")).toBeInTheDocument();
    expect(newsArticleLd(e).datePublished).toBe("2026-09-27T20:45:00Z");
  });

  it("prints nothing when no report carries a time, rather than a guess", () => {
    render(<StoryView event={event([SRC("a1", "thehindu", null)])} />);
    expect(screen.queryByText(/First reported/)).toBeNull();
  });
});
