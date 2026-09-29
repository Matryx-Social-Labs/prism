import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StoryView } from "@/components/StoryView";
import type { EventDetail } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  // The regions list never arrives: the hub states must not need it.
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []), fetchTrendingStory: vi.fn(async () => null), fetchRegions: vi.fn(() => new Promise(() => {})) };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [{ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }],
  lensMeta: () => ({ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }),
}));

function event(over: Partial<EventDetail> = {}): EventDetail {
  return {
    id: "e1", title: "A story", summary: "Rajasthan and Karnataka both reported.", sector: "politics", subsector: null, subject_path: "politics",
    image_url: null, regions: ["IN", "IN-KA", "IN-AS"], occurred_at: "2026-09-04T18:00:00Z", last_updated_at: "2026-09-10T00:00:00Z",
    projection: {}, lens_briefs: { reader: "The reader take." }, lens_points: {}, available_lenses: ["reader"], coverage: null,
    entities: [
      { name: "Karnataka", slug: "karnataka", entity_type: "place", indexable: true },
      { name: "Rajasthan", slug: "rajasthan", entity_type: "place", indexable: true },
      { name: "DK Shivakumar", slug: "dk-shivakumar", entity_type: "person", indexable: true },
    ],
    sources: [], perspectives: [], impacts: [], claims: [],
    ...over,
  } as unknown as EventDetail;
}

const HUBS = { "IN-KA": true, "IN-AS": false, "IN-RJ": false };
const named = () => within(screen.getByRole("heading", { name: "Named in the reports" }).parentElement!);

beforeEach(() => localStorage.clear());

// Audit 02, P1-1: the record's place labels were plain text, and a state's own
// name linked the entity page that the hub now replaces.
describe("the record's places link their state hub", () => {
  it("links a region to its hub when the hub asks to be indexed, and leaves it plain when not", () => {
    render(<StoryView event={event()} hubs={HUBS} />);
    expect(named().getByRole("link", { name: "Karnataka" })).toHaveAttribute("href", "/state/karnataka");
    expect(named().getByRole("link", { name: "Karnataka" })).not.toHaveAttribute("rel");
    expect(named().queryByRole("link", { name: "Assam" })).toBeNull();
    expect(named().getByText("Assam")).toBeInTheDocument();
  });

  it("sends a state's own name to its hub, followed no further than the hub", () => {
    render(<StoryView event={event()} hubs={HUBS} />);
    const rajasthan = named().getByRole("link", { name: "Rajasthan" });
    expect(rajasthan).toHaveAttribute("href", "/state/rajasthan");
    expect(rajasthan).toHaveAttribute("rel", "nofollow");
    expect(named().getByRole("link", { name: "DK Shivakumar" })).toHaveAttribute("href", "/entity/dk-shivakumar");
  });

  it("marks the state's name in the summary with the same link", () => {
    render(<StoryView event={event()} hubs={HUBS} />);
    const marks = [...document.querySelectorAll("header a")].filter((a) => a.textContent === "Rajasthan");
    expect(marks.length).toBeGreaterThan(0);
    for (const a of marks) {
      expect(a).toHaveAttribute("href", "/state/rajasthan");
      expect(a).toHaveAttribute("rel", "nofollow");
    }
  });

  it("keeps region chips plain when the hubs are not known", () => {
    render(<StoryView event={event()} />);
    expect(named().queryByRole("link", { name: "Assam" })).toBeNull();
    expect(named().getByText("Karnataka").closest("a")).toBeNull();
  });
});
