import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

// The live proofs are covered by app/about/page.test.tsx; this file pins what
// the landing must never do: send a visitor back to `/` (which would show them
// this page again), or pass off a written example as the record.
const fetchFeed = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchFeed, fetchEvent: vi.fn(), fetchTrendingStory: vi.fn() };
});
vi.mock("@/lib/lenses", () => ({ useLenses: () => [{ slug: "reader", name: "General reader", plain: "what happened", color: "var(--lens-general)" }] }));

import { Landing } from "@/components/Landing";

beforeEach(() => fetchFeed.mockReset().mockResolvedValue([]));

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
    expect(screen.getByText(/one live record per story: what changed, who said what, exactly, and which outlets covered it/)).toBeInTheDocument();
  });

  it("renders the live registry, not a typed list of lenses", async () => {
    render(await Landing());
    expect(screen.getByText("General reader")).toBeInTheDocument();
  });
});
