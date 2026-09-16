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
  it("sends every 'Read today's chart' action to /feed, never to /", async () => {
    render(await Landing());
    const actions = screen.getAllByRole("link", { name: "Read today's chart" });
    expect(actions.length).toBeGreaterThan(0);
    for (const a of actions) expect(a).toHaveAttribute("href", "/feed");
  });

  it("labels the two written pieces as illustrations and names what is being built next", async () => {
    render(await Landing());
    // the flip demo and the Ask example; nothing else on the page is written
    expect(screen.getAllByText(/^Illustration$/)).toHaveLength(2);
    expect(screen.getByRole("heading", { name: "Being built next" })).toBeInTheDocument();
    for (const t of ["Both sides", "What happens next", "Blindspots"]) expect(screen.getByRole("heading", { name: t })).toBeInTheDocument();
  });

  it("renders the live registry, not a typed list of lenses", async () => {
    render(await Landing());
    expect(screen.getByText("General reader")).toBeInTheDocument();
  });
});
