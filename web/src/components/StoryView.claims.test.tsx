/**
 * "Who said what" — the perspectives layer's read surface.
 *
 * Every assertion here is a product rule, not a render check: verified text in
 * the record voice, [n] in mono and the same index Coverage uses, the link
 * opens the article on the quote, and nothing at all when there is nothing to
 * say. jsdom renders both the mobile and desktop trees, so queries use
 * getAllBy* / scope.
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
  it("renders speaker, verbatim quote, the mono [n] and a link that opens the article on the quote", () => {
    render(<StoryView event={withClaims([
      { speaker: "Anita Dipke", claims: [{ quote_text: QUOTE, quote_start: 1, quote_end: 2,
        article_id: "a2", source_name: "The Hindu", url: "https://x.example/a2",
        published_at: "2026-07-27T10:00:00Z" }] },
    ])} />);
    const section = screen.getAllByRole("region", { name: /who said what/i })[0];
    expect(within(section).getByText("Anita Dipke")).toBeInTheDocument();
    const bq = within(section).getByText(`“${QUOTE}”`);
    // DESIGN.md: the quote is the record voice, never mono.
    expect(bq.tagName).toBe("BLOCKQUOTE");
    expect(bq.className).toMatch(/font-record/);
    expect(bq.className).not.toMatch(/font-mono/);
    // The link's accessible name says where it goes (a screen reader listing
    // links must not hear "Open at the quote" five times) and the [n] beside
    // it is the SAME number Coverage gives that article.
    const cite = within(section).getByRole("link", { name: "Source 2: The Hindu" });
    expect(within(section).getByText("[2]").className).toMatch(/font-mono/);
    // The link opens the article ON the quote: the URL carries a text fragment.
    expect(cite.getAttribute("href")).toMatch(/^https:\/\/x\.example\/a2#:~:text=/);
    expect(within(section).getByText("The Hindu")).toBeInTheDocument();
  });

  it("uses one index for Sources and for citations, so they cannot disagree", () => {
    render(<StoryView event={withClaims([
      { speaker: "X", claims: [{ quote_text: QUOTE, quote_start: 0, quote_end: 0, article_id: "a3",
        source_name: "PTI", url: null, published_at: null }] },
    ])} />);
    const sources = screen.getAllByRole("region", { name: /^coverage/i })[0];
    const said = screen.getAllByRole("region", { name: /who said what/i })[0];
    // a3 is third in event.sources → [3] in both places; a3 has no url → no "open" link
    expect(within(sources).getAllByText("[3]").length).toBeGreaterThan(0);
    expect(within(said).getByText("[3]").tagName).toBe("SPAN");
    expect(within(said).queryByRole("link", { name: /Source 3/ })).toBeNull();
  });

  it("prints who the speaker is when the articles said, under the name", () => {
    render(<StoryView event={withClaims([
      { speaker: "J.D. Vance", role: "Vice President of the United States", claims: [{ quote_text: QUOTE, quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "u", published_at: null }] },
      { speaker: "Someone", role: null, claims: [{ quote_text: QUOTE + "?", quote_start: 0, quote_end: 0, article_id: "a2", source_name: "H", url: "u", published_at: null }] },
    ])} />);
    const said = screen.getAllByRole("region", { name: /who said what/i })[0];
    expect(within(said).getByText("Vice President of the United States")).toBeInTheDocument();
    // a speaker without a stated role gets no line, not an empty one
    expect(within(said).getByText("Someone").parentElement!.querySelectorAll("p")).toHaveLength(1);
  });

  it("shows one speaker once with a count when they have several quotes", () => {
    render(<StoryView event={withClaims([
      { speaker: "Jose Pradeep", claims: [
        { quote_text: "first thing said here at length", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "u", published_at: null },
        { quote_text: "second thing said here at length", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "u", published_at: null },
      ] },
    ])} />);
    const said = screen.getAllByRole("region", { name: /who said what/i })[0];
    expect(within(said).getAllByText("Jose Pradeep")).toHaveLength(1);
    const count = within(said).getByText(/2 quotes · 1 outlet/);
    expect(count).toBeInTheDocument();
    expect(count.className).not.toMatch(/font-mono/); // a bare count is UI voice
  });

  it("renders NOTHING when there are no claims — no section, no chip", () => {
    render(<StoryView event={withClaims([])} />);
    expect(screen.queryByRole("region", { name: /who said what/i })).not.toBeInTheDocument();
    expect(screen.queryByRole("link", { name: /^Who said what/ })).not.toBeInTheDocument();
  });

  it("survives a payload with no claims field at all (old backend, cached response)", () => {
    // Vercel and Railway deploy from two pipelines and /events is cached 60s, so a
    // new page WILL meet an old payload for a window. It must not crash.
    render(<StoryView event={withClaims(undefined)} />);
    expect(screen.getAllByText("A story").length).toBeGreaterThan(0);
    expect(screen.queryByRole("region", { name: /who said what/i })).not.toBeInTheDocument();
  });

  it("puts the count in the section nav", () => {
    render(<StoryView event={withClaims([
      { speaker: "A", claims: [{ quote_text: QUOTE, quote_start: 0, quote_end: 0, article_id: "a1", source_name: "Mint", url: "u", published_at: null }] },
      { speaker: "B", claims: [{ quote_text: QUOTE + "!", quote_start: 0, quote_end: 0, article_id: "a2", source_name: "H", url: "u", published_at: null }] },
    ])} />);
    const item = screen.getByRole("link", { name: /^Who said what/ });
    expect(item).toHaveTextContent("2");
    expect(item).toHaveAttribute("href", "#said");
  });
});


describe("Who said what — the quote in the article", () => {
  it("shows the article's own words around the quote when the server sends them, folded", () => {
    render(<StoryView event={withClaims([
      { speaker: "Anita Dipke", claims: [{ quote_text: QUOTE, quote_start: 20, quote_end: 30, context_before: "Earlier that day,", context_after: "she added later.", article_id: "a2", source_name: "The Hindu", url: "https://x.example/a2", published_at: null }] },
    ])} />);
    expect(screen.getByText("In the article")).toBeInTheDocument();
    expect(screen.getByText(/Earlier that day,/)).toBeInTheDocument();
    expect(screen.getByText(/she added later\./)).toBeInTheDocument();
  });
});
