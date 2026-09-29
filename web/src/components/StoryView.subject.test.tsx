import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StoryView } from "@/components/StoryView";
import type { EventDetail } from "@/lib/api";

const fetchTrendingStory = vi.hoisted(() => vi.fn());
vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []), fetchTrendingStory };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [{ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }],
  lensMeta: () => ({ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }),
}));

function event(over: Partial<EventDetail> = {}): EventDetail {
  return {
    id: "e1", title: "A story", summary: "A summary.", sector: "politics", subsector: null, subject_path: "politics.elections",
    image_url: null, regions: [], occurred_at: "2026-09-04T18:00:00Z", last_updated_at: "2026-09-10T00:00:00Z",
    projection: {}, lens_briefs: { reader: "The reader take." }, lens_points: {}, available_lenses: ["reader"],
    coverage: null, entities: [], sources: [], perspectives: [], impacts: [], claims: [],
    ...over,
  } as unknown as EventDetail;
}

const TRAIL = [
  { name: "Politics", href: "/sector/politics" },
  { name: "Elections", href: "/subject/politics/elections" },
];

beforeEach(() => {
  localStorage.clear();
  fetchTrendingStory.mockReset().mockResolvedValue(null);
});

// Audit A2: 26,220 records printed their subject as plain text, so the subject
// pages under the six groups had no link from the records they list.
describe("the record links its subject", () => {
  it("links the deepest subject node from the meta line", () => {
    render(<StoryView event={event()} trail={TRAIL} />);
    const meta = document.querySelector("header .meta-line") as HTMLElement;
    expect(within(meta).getByRole("link", { name: "Elections" })).toHaveAttribute("href", "/subject/politics/elections");
  });

  it("prints the trail Today › group › node above the title, on a desk only", () => {
    render(<StoryView event={event()} trail={TRAIL} />);
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" });
    expect(within(nav).getAllByRole("link").map((a) => [a.textContent, a.getAttribute("href")])).toEqual([
      ["Today", "/feed"],
      ["Politics", "/sector/politics"],
      ["Elections", "/subject/politics/elections"],
    ]);
    expect(nav).toHaveClass("hidden", "lg:block");
    expect(nav.compareDocumentPosition(screen.getByRole("heading", { level: 1 })) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("links the sector group when the page has no labelled trail to give", () => {
    render(<StoryView event={event({ subject_path: null })} />);
    const meta = document.querySelector("header .meta-line") as HTMLElement;
    expect(within(meta).getByRole("link", { name: "Politics" })).toHaveAttribute("href", "/sector/politics");
  });
});

// Audit A5: a provisional grouping's page asks not to be indexed.
describe("the foot link to the story's grouping", () => {
  const story = (boundary_status: "provisional" | "verified") => ({
    slug: "s", canonical_slug: "s", label: "L", cast: [], sector: null, source_count: 3, velocity: 0, status: "active",
    boundary_status, developments: [], timeline_cast: [], branches: null, related: [],
  });

  it("is nofollow while the boundary is provisional", async () => {
    fetchTrendingStory.mockResolvedValue(story("provisional"));
    render(<StoryView event={event({ story_slug: "s" })} trail={TRAIL} />);
    await screen.findByText("Provisional grouping");
    expect(screen.getByRole("link", { name: /Open the grouping/ })).toHaveAttribute("rel", "nofollow");
  });

  // Review 2026-09-29: the status arrives from a client fetch, so the server
  // HTML (all a non-rendering crawler reads) must not guess "provisional" and
  // nofollow a verified story's link from every record.
  it("says nothing until the status is known", () => {
    fetchTrendingStory.mockReturnValue(new Promise(() => {}));
    render(<StoryView event={event({ story_slug: "s" })} trail={TRAIL} />);
    expect(screen.getByRole("link", { name: /Open the grouping/ })).not.toHaveAttribute("rel");
  });

  it("is followed once the boundary is verified", async () => {
    fetchTrendingStory.mockResolvedValue(story("verified"));
    render(<StoryView event={event({ story_slug: "s" })} trail={TRAIL} />);
    expect(await screen.findByRole("link", { name: /The whole story/ })).not.toHaveAttribute("rel");
  });
});
