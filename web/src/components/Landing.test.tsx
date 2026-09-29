import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { EventDetail, FeedItem } from "@/lib/api";

// The landing's promise is that nothing on it is written for the page: every
// headline, count, quote, brief and price comes from the product. This file
// pins that, and what the landing must never do: send a visitor back to `/`
// (which would show them this page again), or pass off a written example as
// the record.
const fetchFeed = vi.hoisted(() => vi.fn());
const fetchSources = vi.hoisted(() => vi.fn());
const fetchEvent = vi.hoisted(() => vi.fn());
const fetchPlans = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchFeed, fetchSources, fetchEvent, fetchTrendingStory: vi.fn() };
});
vi.mock("@/lib/billing", async () => {
  const actual = await vi.importActual<typeof import("@/lib/billing")>("@/lib/billing");
  return { ...actual, fetchPlans };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [
    { slug: "reader", name: "General reader", short: "Reader", plain: "what happened", tagline: "", color: "var(--ink)", bg: "var(--sunken)" },
    { slug: "markets", name: "Finance / Trader", short: "Markets", plain: "what this moves in the market, and why", tagline: "", color: "var(--lens-markets)", bg: "var(--lens-markets-soft)" },
  ],
}));

import { Landing } from "@/components/Landing";

const outlet = (p: string) => ({ slug: p, publisher: p, name: p, code: p.toUpperCase(), origin: "national", language: "en", domain: null });
const row = (id: string, over: Partial<FeedItem> = {}): FeedItem =>
  ({ id, title: `Story ${id}`, sector: "politics", source_count: 3, last_updated_at: "2026-09-24T00:00:00Z", regions: [], outlets: [outlet("th"), outlet("ht"), outlet("mint")], ...over }) as unknown as FeedItem;
const src = (id: string, name: string) => ({
  article_id: id, source_name: name, source_slug: name, url: `https://example.com/${id}`, title: `Report ${id}`, published_at: `2026-09-24T0${id.slice(-1)}:00:00Z`,
  funding: null, code: name.slice(0, 2).toUpperCase(), origin: "national", language: "en", publisher: name, domain: null, image_url: null,
});
const record = (id: string): EventDetail =>
  ({
    id, title: `Story ${id}`, summary: null, sector: "politics", subsector: null, image_url: null, regions: [], occurred_at: null,
    last_updated_at: "2026-09-24T00:00:00Z", coverage: null, entities: [], projection: null, perspectives: [], impacts: [],
    sources: [src("a1", "The Hindu"), src("a2", "Mint"), src("a3", "Reuters"), src("a4", "Scroll")],
    lens_briefs: { reader: "The council voted to widen the road." },
    lens_points: { reader: ["Whether the plan is notified"] },
    available_lenses: ["reader", "markets"],
    claims: [{ speaker: "Anita Dipke", role: "Minister", claims: [{ quote_text: "We were receiving proposals from every ward", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "The Hindu", url: "https://example.com/a1", published_at: null }] }],
  }) as unknown as EventDetail;

beforeEach(() => {
  fetchFeed.mockReset().mockResolvedValue([]);
  fetchSources.mockReset().mockResolvedValue(null);
  fetchEvent.mockReset().mockRejectedValue(new Error("no record in this test"));
  fetchPlans.mockReset().mockRejectedValue(new Error("no plans in this test"));
});

describe("Landing", () => {
  it("sends every 'Read today’s record' action to /feed, never to /", async () => {
    render(await Landing());
    const actions = screen.getAllByRole("link", { name: /Read today’s record/ });
    expect(actions.length).toBeGreaterThan(0);
    for (const a of actions) expect(a).toHaveAttribute("href", "/feed");
  });

  it("shows no written illustration anywhere, and separates current work from future work", async () => {
    fetchFeed.mockResolvedValue([row("lead"), row("two")]);
    fetchEvent.mockImplementation(async (id: string) => record(id));
    render(await Landing());
    expect(screen.queryByText(/illustration/i)).toBeNull();
    expect(screen.getByRole("heading", { name: "What works today, and what’s next" })).toBeInTheDocument();
    for (const t of ["Working now", "Being checked", "Next"]) {
      expect(screen.getByRole("heading", { name: t })).toBeInTheDocument();
    }
  });

  it("leads with the product's narrower, verifiable promise", async () => {
    render(await Landing());
    expect(screen.getByRole("heading", { name: "Follow the story, not the headlines." })).toBeInTheDocument();
    // Evidence first (strategy report, 2026-09-24): what is kept, not what is summarised.
    expect(screen.getByText(/See who said what, word for word, and which outlets covered it/)).toBeInTheDocument();
    // The truth layer is never the premium feature.
    expect(screen.getByText(/The evidence is free and stays free/)).toBeInTheDocument();
  });

  it("counts today's outlets out of the monitored set, never as a bare total", async () => {
    fetchFeed.mockResolvedValue([row("a", { outlets: [outlet("th"), outlet("ht")] }), row("b", { outlets: [outlet("th")] })]);
    fetchSources.mockResolvedValue({ outlets: 27, checked_at: null, feeds: [] });
    render(await Landing());
    expect(screen.getByText("of 27 monitored outlets in today's record")).toBeInTheDocument();
  });

  it("builds the proof and the lens flip from one real record, and flips a paid lens to the story, not to a sample", async () => {
    fetchFeed.mockResolvedValue([row("lead"), row("two")]);
    fetchEvent.mockImplementation(async (id: string) => record(id));
    render(await Landing());
    // What changed: the record's newest reports, newest first.
    const newest = screen.getByRole("list", { name: "The newest reports, newest first" });
    expect(within(newest).getAllByRole("link").map((a) => a.textContent?.trim())).toEqual(["Report a4", "Report a3", "Report a2"]);
    // Exact words: the verified quote, as the article printed it.
    expect(screen.getByText(/We were receiving proposals from every ward/)).toBeInTheDocument();
    // The flip: the record's own brief, then the professional lens is read on the story.
    expect(screen.getByText("The council voted to widen the road.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("tab", { name: /Markets/ }));
    expect(screen.queryByText("The council voted to widen the road.")).toBeNull();
    expect(screen.getByRole("link", { name: "Read it on the story" })).toHaveAttribute("href", "/story/lead");
  });

  it("showcases words two outlets printed, not whatever the record lists first", async () => {
    // Audit P0 #2: the landing took claims[0], and printed Majithia's post on X
    // as the SSP's. It now leads with a checked quote more than one outlet carried.
    fetchFeed.mockResolvedValue([row("lead")]);
    fetchEvent.mockImplementation(async (id: string) => ({
      ...record(id),
      claims: [
        { speaker: "Naveen Singla", role: "DIG", claims: [{ id: "s1", quote_text: "We are verifying the facts on the ground", quote_start: 0, quote_end: 0, article_id: "a1", source_name: "The Hindu", url: null, published_at: null }] },
        {
          speaker: "Gaurav Toora", role: null,
          claims: [{ id: "t1", quote_text: "When we reached here, we came to know there were rumours", quote_start: 0, quote_end: 0, article_id: "a2", source_name: "Mint", url: null, published_at: null,
            also_in: [{ id: "t1", article_id: "a3", source_name: "Reuters", url: null, published_at: null }] }],
        },
      ],
    }));
    render(await Landing());
    expect(screen.getByText(/When we reached here/)).toBeInTheDocument();
    expect(screen.queryByText(/We are verifying the facts/)).toBeNull();
  });

  it("prints the Plus price only from the pricing source", async () => {
    render(await Landing());
    expect(screen.getByRole("heading", { name: "Prism Plus" })).toBeInTheDocument();
    fetchPlans.mockResolvedValue({ plans: [{ plan: "plus_yearly", label: "", amount_paise: 119900, period: "year" }, { plan: "plus_monthly", label: "", amount_paise: 14900, period: "month" }] });
    render(await Landing());
    expect(screen.getByRole("heading", { name: "Prism Plus · from ₹149 a month" })).toBeInTheDocument();
  });

  // Founder decision #2 (27 Sep): Plus sells the lenses and Ask, never a model.
  it("says Plus opens every lens, and sells no model", async () => {
    render(await Landing());
    const card = screen.getByRole("heading", { name: "Prism Plus" }).parentElement!;
    expect(card).toHaveTextContent(/Every lens on every story/);
    expect(card.textContent).not.toMatch(/model/i);
  });

  // The FAQ's JSON-LD must say exactly what the page shows: markup that
  // differs from the visible text is what search engines penalise.
  it("carries FAQPage JSON-LD whose answers are the visible answers", async () => {
    const { container } = render(await Landing());
    const ld = [...container.querySelectorAll('script[type="application/ld+json"]')]
      .map((el) => JSON.parse(el.textContent ?? "{}"))
      .find((d) => d["@type"] === "FAQPage");
    expect(ld).toBeDefined();
    expect(ld.mainEntity.length).toBeGreaterThan(0);
    for (const q of ld.mainEntity) {
      const summary = screen.getByText(q.name, { selector: "summary span" });
      expect(summary.closest("details")).toHaveTextContent(q.acceptedAnswer.text);
    }
  });

  // Audit 2026-09-29: the hero said "Live · updated 1d ago" with a pulsing dot
  // while ingestion had been paused for a day.
  it("calls the lead live only while its newest report is recent", async () => {
    const recent = new Date(Date.now() - 20 * 60 * 1000).toISOString();
    fetchFeed.mockResolvedValue([row("lead", { latest_published_at: recent } as Partial<FeedItem>)]);
    render(await Landing());
    expect(screen.getByText(/Live · updated/)).toBeInTheDocument();

    fetchFeed.mockResolvedValue([row("lead", { latest_published_at: "2026-09-01T00:00:00Z" } as Partial<FeedItem>)]);
    const { container } = render(await Landing());
    expect(within(container).queryByText(/Live · updated/)).toBeNull();
    expect(within(container).getByText(/^Updated/)).toBeInTheDocument();
  });

  it("prints no typed figure among the counted ones", async () => {
    fetchFeed.mockResolvedValue([row("a")]);
    fetchSources.mockResolvedValue({ outlets: 27, checked_at: null, feeds: [{ language: "en" }, { language: "hi" }] });
    render(await Landing());
    expect(screen.queryByText("record per story")).toBeNull();
    expect(screen.getByText("of 2 monitored languages in today's record")).toBeInTheDocument();
  });

  it("falls back to the live lens registry when no record carries a brief", async () => {
    render(await Landing());
    expect(screen.getByText("General reader")).toBeInTheDocument();
  });
});
