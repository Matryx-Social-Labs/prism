import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// The live proofs are covered by app/about/page.test.tsx; this file pins what
// the landing must never do: send a visitor back to `/` (which would show them
// this page again), or pass off a written example as the record.
const fetchFeed = vi.hoisted(() => vi.fn());
const fetchSources = vi.hoisted(() => vi.fn());
const fetchEvent = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchFeed, fetchSources, fetchEvent, fetchTrendingStory: vi.fn() };
});
vi.mock("@/lib/lenses", () => ({ useLenses: () => [{ slug: "reader", name: "General reader", plain: "what happened", color: "var(--lens-general)" }] }));

import { Landing } from "@/components/Landing";

beforeEach(() => {
  fetchFeed.mockReset().mockResolvedValue([]);
  fetchSources.mockReset().mockResolvedValue(null);
  fetchEvent.mockReset().mockRejectedValue(new Error("no record in this test"));
});

describe("Landing", () => {
  it("sends every 'Open today’s record' action to /feed, never to /", async () => {
    render(await Landing());
    const actions = screen.getAllByRole("link", { name: /Open today’s record/ });
    expect(actions.length).toBeGreaterThan(0);
    for (const a of actions) expect(a).toHaveAttribute("href", "/feed");
  });

  it("labels written interactions as illustrations and separates current work from future work", async () => {
    render(await Landing());
    // the flip demo and the Ask example; live records are never labelled as examples
    expect(screen.getAllByText(/Illustration/)).toHaveLength(2);
    expect(screen.getByRole("heading", { name: "Honest about what’s live." })).toBeInTheDocument();
    for (const t of ["Available now", "In validation", "Next"]) {
      expect(screen.getByRole("heading", { name: t })).toBeInTheDocument();
    }
  });

  it("leads with the product's narrower, verifiable promise", async () => {
    render(await Landing());
    expect(screen.getByRole("heading", { name: "Follow the story, not the headlines." })).toBeInTheDocument();
    // Evidence first (strategy report, 2026-09-24): what is kept, not what is summarised.
    expect(screen.getByText(/keeps the evidence attached: every report, the exact words said, which outlets covered it and how many have not yet/)).toBeInTheDocument();
    // The truth layer is never the premium feature.
    expect(screen.getByText(/The evidence is free and stays free/)).toBeInTheDocument();
  });

  it("counts today's outlets out of the monitored set, never as a bare total", async () => {
    const outlet = (p: string) => ({ slug: p, publisher: p, name: p, code: p.toUpperCase(), origin: "national", language: "en", domain: null });
    fetchFeed.mockResolvedValue([
      { id: "a", title: "A", sector: "politics", source_count: 2, last_updated_at: "2026-09-24T00:00:00Z", regions: [], outlets: [outlet("th"), outlet("ht")] },
      { id: "b", title: "B", sector: "politics", source_count: 1, last_updated_at: "2026-09-24T00:00:00Z", regions: [], outlets: [outlet("th")] },
    ]);
    fetchSources.mockResolvedValue({ outlets: 27, checked_at: null, feeds: [] });
    render(await Landing());
    expect(screen.getByText("of 27 monitored outlets in today's record")).toBeInTheDocument();
  });

  it("renders the live registry, not a typed list of lenses", async () => {
    render(await Landing());
    expect(screen.getByText("General reader")).toBeInTheDocument();
  });
});
