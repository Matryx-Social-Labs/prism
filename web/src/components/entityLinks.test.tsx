import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StoryView } from "@/components/StoryView";
import { StoryArc } from "@/components/reading/StoryArc";
import type { EventDetail, TrendingStoryDetail } from "@/lib/api";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }), usePathname: () => "/" }));
vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return { ...actual, fetchBrief: vi.fn(async () => null), fetchQuestions: vi.fn(async () => []) };
});
vi.mock("@/lib/lenses", () => ({
  useLenses: () => [{ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }],
  lensMeta: () => ({ slug: "reader", short: "Reader", color: "#111", bg: "#eee", tagline: "t" }),
}));

// 85% of the entity pages crawlers fetched were stubs that ask not to be
// indexed (2026-09-27); they found them through these links. A link to a stub
// says nofollow; a link to a page worth indexing stays a plain link.
const EVENT = {
  id: "e1", title: "A story", summary: "Mumbai Police questioned Asha Rao.", sector: "politics", subsector: null,
  image_url: null, regions: [], occurred_at: "2026-07-01T00:00:00Z", last_updated_at: "2026-07-01T00:00:00Z",
  projection: {}, lens_briefs: { reader: "The reader take." }, lens_points: {}, available_lenses: ["reader"],
  coverage: null, sources: [], perspectives: [], impacts: [], claims: [],
  entities: [
    { name: "Mumbai Police", entity_type: "organization", role: "actor", slug: "mumbai-police", indexable: true },
    { name: "Asha Rao", entity_type: "person", role: "subject", slug: "asha-rao", indexable: false },
  ],
} as unknown as EventDetail;

const links = (href: string) => screen.getAllByRole("link").filter((a) => a.getAttribute("href") === href);

describe("links to actor pages", () => {
  it("say nofollow on a record only where the actor's page is a stub", () => {
    render(<StoryView event={EVENT} />);
    const stub = links("/entity/asha-rao");
    const hub = links("/entity/mumbai-police");
    // Both the chip under "Named in the reports" and the mark in the summary.
    expect(stub.length).toBeGreaterThanOrEqual(2);
    expect(hub.length).toBeGreaterThanOrEqual(2);
    stub.forEach((a) => expect(a).toHaveAttribute("rel", "nofollow"));
    hub.forEach((a) => expect(a).not.toHaveAttribute("rel"));
  });

  it("say nofollow in a story's cast only where the actor's page is a stub", () => {
    const s = {
      slug: "s", canonical_slug: "s", label: "A story", sector: "politics", source_count: 3, velocity: 1,
      developments: [], outlets: [], photos: [], boundary_status: "provisional", branches: null, related: [],
      last_updated_at: null, shared_cast: [], causal: false,
      cast: ["Mumbai Police", "Asha Rao", "Nobody"],
      cast_refs: [
        { name: "Mumbai Police", slug: "mumbai-police", indexable: true },
        { name: "Asha Rao", slug: "asha-rao", indexable: false },
        { name: "Nobody", slug: null, indexable: false },
      ],
    } as unknown as TrendingStoryDetail;
    render(<StoryArc s={s} />);
    const cast = within(screen.getByRole("region", { name: /Who is in it/ }));
    expect(cast.getByRole("link", { name: "Asha Rao" })).toHaveAttribute("rel", "nofollow");
    expect(cast.getByRole("link", { name: "Mumbai Police" })).not.toHaveAttribute("rel");
    expect(cast.queryByRole("link", { name: "Nobody" })).toBeNull();
  });
});
