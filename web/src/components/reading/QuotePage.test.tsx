import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { ClaimOut, EventDetail } from "@/lib/api";
import QuotePage from "@/app/story/[id]/quote/[n]/page";

const fetchEvent = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => ({ ...(await vi.importActual<typeof import("@/lib/api")>("@/lib/api")), fetchEvent }));
vi.mock("next/navigation", () => ({ notFound: () => { throw new Error("NEXT_NOT_FOUND"); } }));

const claim = (over: Partial<ClaimOut> = {}): ClaimOut => ({
  quote_text: "We will reopen the bridge on Monday.",
  quote_start: null,
  quote_end: null,
  context_before: "The minister told reporters",
  context_after: "Traffic police will manage the diversion.",
  article_id: "a2",
  source_name: "The Hindu",
  url: "https://x.test/a2",
  published_at: "2026-09-24T06:00:00Z",
  lang: "en",
  translated: false,
  ...over,
});

const event = (c: ClaimOut): EventDetail =>
  ({
    id: "e1",
    title: "Bridge reopens",
    summary: null,
    sector: "politics",
    subsector: null,
    image_url: null,
    regions: [],
    occurred_at: null,
    last_updated_at: "2026-09-24T06:00:00Z",
    projection: {},
    lens_briefs: {},
    lens_points: {},
    available_lenses: [],
    coverage: null,
    entities: [],
    sources: [
      { article_id: "a1", source_name: "Mint", source_slug: "mint", code: "LM", origin: "national", url: null, title: "r", published_at: null, funding: null },
      { article_id: "a2", source_name: "The Hindu", source_slug: "hindu", code: "TH", origin: "national", url: null, title: "r", published_at: null, funding: null },
    ],
    perspectives: [],
    impacts: [],
    claims: [{ speaker: "A Minister", role: "Minister of Roads", claims: [c] }],
  }) as unknown as EventDetail;

const open = async (id = "0-0") => render(await QuotePage({ params: Promise.resolve({ id: "e1", n: id }) }));

beforeEach(() => fetchEvent.mockReset());

describe("/story/[id]/quote/[n] — the quote's own page", () => {
  it("prints the words, who said them, where and when, and the article around them", async () => {
    fetchEvent.mockResolvedValue(event(claim()));
    await open();
    expect(screen.getByText("“We will reopen the bridge on Monday.”")).toBeInTheDocument();
    expect(screen.getByText("A Minister")).toBeInTheDocument();
    expect(screen.getByText("Minister of Roads")).toBeInTheDocument();
    // [n] is the report's place in the record's own list, the index the story page uses.
    expect(screen.getByText(/^THE HINDU · \[2\] · 24 SEPT/)).toBeInTheDocument();
    expect(screen.getByText("Word for word, checked against the article.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Open at the quote/ }).getAttribute("href")).toMatch(/^https:\/\/x\.test\/a2#:~:text=/);
    expect(screen.getByRole("heading", { name: "In the article" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Bridge reopens/ })).toHaveAttribute("href", "/story/e1");
  });

  it("says the outlet translated the words, never that they are word for word", async () => {
    fetchEvent.mockResolvedValue(event(claim({ lang: "hi", translated: true, quote_text: "सोमवार को पुल खुलेगा।" })));
    await open();
    expect(screen.getByText("Checked against the article. The outlet translated these words.")).toBeInTheDocument();
    expect(screen.queryByText("Word for word, checked against the article.")).not.toBeInTheDocument();
    expect(screen.getByText("translation")).toBeInTheDocument();
  });

  it("leaves out the article's words when the span could not be re-verified, and 404s an unknown quote", async () => {
    fetchEvent.mockResolvedValue(event(claim({ context_before: "", context_after: "" })));
    await open();
    expect(screen.queryByRole("heading", { name: "In the article" })).not.toBeInTheDocument();
    await expect(open("3-0")).rejects.toThrow("NEXT_NOT_FOUND");
  });
});
