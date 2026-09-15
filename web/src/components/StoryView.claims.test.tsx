/**
 * "What was said" — the perspectives layer's first read surface.
 *
 * Every assertion here is a product rule, not a render check: verified text in
 * the body voice, provenance in mono, the citation IS the link, and nothing at
 * all when there is nothing to say. jsdom renders both the mobile and desktop
 * trees, so queries use getAllBy* / scope.
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

const SRC = (id: string, name: string, url: string | null = `https://x.example/${id}`) => ({
  article_id: id, source_name: name, source_slug: name.toLowerCase(), url, title: `T ${id}`,
  published_at: "2026-07-27T10:00:00Z", stance: null, funding: null,
});

const BASE = {
  id: "e1", title: "A story", summary: "S", sector: "news", subsector: null, image_url: null,
  regions: [], occurred_at: "2026-07-01T00:00:00Z", last_updated_at: "2026-07-01T00:00:00Z",
  projection: {}, lens_briefs: { reader: "brief" }, lens_points: {}, available_lenses: ["reader"],
  coverage: null, entities: [], perspectives: [], impacts: [],
  sources: [SRC("a1", "Mint"), SRC("a2", "The Hindu"), SRC("a3", "PTI", null)],
};

const QUOTE = "We were receiving marriage proposals for Abhijeet even before the CJP protest started";

function withClaims(claims: unknown): EventDetail {
  return { ...BASE, claims } as unknown as EventDetail;
}

beforeEach(() => localStorage.clear());

describe("What was said", () => {
  it("renders speaker, verbatim quote, and a mono citation that links to the article", () => {
    render(<StoryView event={withClaims([
      { speaker: "Anita Dipke", claims: [{ quote_text: QUOTE, quote_start: 1, quote_end: 2,
        article_id: "a2", source_name: "The Hindu", url: "https://x.example/a2",
        published_at: "2026-07-27T10:00:00Z" }] },
    ])} />);
    const section = screen.getAllByRole("region", { name: /what was said/i })[0];
    expect(within(section).getByText("Anita Dipke")).toBeInTheDocument();
    const bq = within(section).getByText(`“${QUOTE}”`);
    // DESIGN.md: mono is provenance only. The quote and the speaker are the body voice.
    expect(bq.tagName).toBe("BLOCKQUOTE");
    expect(bq.className).not.toMatch(/font-mono/);
    // The citation is the link, its accessible name says where it goes (a screen
    // reader listing links must not hear "[2]" five times), and it is the SAME
    // number Sources gives that article.
    const cite = within(section).getByRole("link", { name: "Source 2: The Hindu" });
    expect(cite).toHaveTextContent("[2]");
    expect(cite).toHaveAttribute("href", "https://x.example/a2");
    expect(cite.className).toMatch(/font-mono/);
    expect(within(section).getByText("The Hindu")).toBeInTheDocument();
    expect(within(section).getByText("· 27 Jul")).toBeInTheDocument();
  });

  it("uses one index for Sources and for citations, so they cannot disagree", () => {
    render(<StoryView event={withClaims([
      { speaker: "X", claims: [{ quote_text: QUOTE, quote_start: 0, quote_end: 0, article_id: "a3",
        source_name: "PTI", url: null, published_at: null }] },
    ])} />);
    const sources = screen.getAllByRole("region", { name: /^sources/i })[0];
    const said = screen.getAllByRole("region", { name: /what was said/i })[0];
    // a3 is third in event.sources → [3] in both places; a3 has no url → plain text citation
    expect(within(sources).getAllByText("[3]").length).toBeGreaterThan(0);
    expect(within(said).getByText("[3]").tagName).toBe("SPAN");
  });

  it("shows one speaker once with a count when they have several quotes", () => {
    render(<StoryView event={withClaims([
      { speaker: "Jose Pradeep", claims: [
        { quote_text: "first thing said here at length", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "u", published_at: null },
        { quote_text: "second thing said here at length", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "u", published_at: null },
      ] },
    ])} />);
    const said = screen.getAllByRole("region", { name: /what was said/i })[0];
    expect(within(said).getAllByText("Jose Pradeep")).toHaveLength(1);
    const count = within(said).getByText("2 quotes");
    expect(count).toBeInTheDocument();
    expect(count.className).not.toMatch(/font-mono/); // a bare count is UI voice, like "Sources (n)"
  });

  it("renders NOTHING when there are no claims — no section, no chip", () => {
    render(<StoryView event={withClaims([])} />);
    expect(screen.queryByRole("region", { name: /what was said/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^Said/ })).not.toBeInTheDocument();
  });

  it("survives a payload with no claims field at all (old backend, cached response)", () => {
    // Vercel and Railway deploy from two pipelines and /events is cached 60s, so a
    // new page WILL meet an old payload for a window. It must not crash.
    render(<StoryView event={withClaims(undefined)} />);
    expect(screen.getAllByText("A story").length).toBeGreaterThan(0);
    expect(screen.queryByRole("region", { name: /what was said/i })).not.toBeInTheDocument();
  });

  it("puts the count in the mobile nav and the desktop rail", () => {
    render(<StoryView event={withClaims([
      { speaker: "A", claims: [{ quote_text: QUOTE, quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "u", published_at: null }] },
      { speaker: "B", claims: [{ quote_text: QUOTE + "!", quote_start: 0, quote_end: 0, article_id: "a2", source_name: "H", url: "u", published_at: null }] },
    ])} />);
    const chip = screen.getByRole("link", { name: /^Said/ });
    expect(chip).toHaveTextContent("2");
    expect(chip).toHaveAttribute("href", "#said");
    expect(screen.getByText("2 quotes", { selector: "div" })).toBeInTheDocument();
  });
});
