/**
 * Every "outlets" count on the record page counts MASTHEADS (audit P0 #8 and the
 * story-page row in P1). One outlet's five reports are one outlet, not yet
 * corroborated; The Times of India and The Times of India — Delhi are one
 * publisher, so the header said "3 outlets" while "Who said what" said "4".
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StoryView } from "@/components/StoryView";
import type { EventDetail } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []) };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [{ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }],
  lensMeta: () => ({ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }),
}));

const SRC = (id: string, slug: string, publisher: string, name: string, code: string) => ({
  article_id: id, source_name: name, source_slug: slug, publisher, code, origin: "national", language: "en",
  url: `https://x.example/${id}`, title: `T ${id}`, published_at: "2026-09-27T10:00:00Z", funding: null,
});

const BASE = {
  id: "e1", title: "A story", summary: "S", sector: "news", subsector: null, image_url: null,
  regions: [], occurred_at: "2026-09-27T00:00:00Z", last_updated_at: "2026-09-27T00:00:00Z",
  projection: {}, lens_briefs: { reader: "brief" }, lens_points: {}, available_lenses: ["reader"],
  coverage: null, entities: [], perspectives: [], impacts: [],
};

const quote = (text: string, article_id: string, source_name: string) => ({
  quote_text: text, quote_start: 0, quote_end: 0, article_id, source_name, url: `https://x.example/${article_id}`, published_at: null,
});

beforeEach(() => localStorage.clear());

describe("outlets are counted by masthead on the record page", () => {
  it("five reports from one newsroom: one outlet, not yet corroborated, one on the coverage legend", () => {
    const sources = [1, 2, 3, 4, 5].map((i) => SRC(`a${i}`, i % 2 ? "ie_india" : "ie_cities", "indianexpress", "The Indian Express", "IE"));
    render(<StoryView event={{ ...BASE, sources } as unknown as EventDetail} />);

    expect(screen.getAllByText("Single source · not yet corroborated").length).toBeGreaterThan(0);
    const coverage = screen.getAllByRole("region", { name: /^coverage/i })[0];
    expect(within(coverage).getByText("1 outlet")).toBeInTheDocument();
    // The legend's count is outlets, the same number the heading prints — not reports.
    expect(within(coverage).getByText("English national").textContent).toBe("English national1");
  });

  it("The Times of India and its Delhi desk are one outlet in Who said what, as in the header", () => {
    const sources = [
      SRC("a1", "toi", "timesofindia", "The Times of India", "TOI"),
      SRC("a2", "toi_delhi", "timesofindia", "The Times of India — Delhi", "TOI"),
      SRC("a3", "thehindu", "thehindu", "The Hindu", "TH"),
    ];
    const claims = [
      { speaker: "Parvesh Verma", claims: [quote("first thing said here at length", "a1", "The Times of India"), quote("second thing said here at length", "a2", "The Times of India — Delhi")] },
      { speaker: "Saheb Singh", claims: [quote("third thing said here at length", "a2", "The Times of India — Delhi")] },
    ];
    render(<StoryView event={{ ...BASE, sources, claims } as unknown as EventDetail} />);

    const said = screen.getAllByRole("region", { name: /who said what/i })[0];
    expect(within(said).getByText("3 quotes · 1 outlet")).toBeInTheDocument();
    // One speaker quoted by both ToI desks: one outlet on the card too.
    expect(within(said).getByText(/2 quotes · 1 outlet/)).toBeInTheDocument();
    const coverage = screen.getAllByRole("region", { name: /^coverage/i })[0];
    expect(within(coverage).getByText("2 outlets")).toBeInTheDocument();
    expect(within(coverage).getByText("English national").textContent).toBe("English national2");
  });
});
