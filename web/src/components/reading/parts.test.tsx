import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DevelopingRail } from "@/components/reading/parts";
import type { TrendingStory } from "@/lib/api";

const story = (slug: string, boundary_status?: "provisional" | "verified"): TrendingStory => ({
  slug, label: `Story ${slug}`, photos: [], cast: [], source_count: 3, velocity: 0, developments: 2, sector: "politics",
  hero_title: null, hero_image: null, hero_event_id: `ev-${slug}`, first_seen_at: null, last_updated_at: null, route: null, boundary_status,
});

// Audit A5: every arc a hub linked was a provisional grouping, whose page asks
// not to be indexed; the rail follows a story only once its boundary is verified.
describe("DevelopingRail — follows only a verified story", () => {
  it("marks a provisional or unverdicted grouping nofollow, and leaves a verified story plain", () => {
    render(<DevelopingRail stories={[story("p", "provisional"), story("u"), story("v", "verified")]} title="Developing here" />);
    expect(screen.getByRole("link", { name: /Story p/ })).toHaveAttribute("rel", "nofollow");
    expect(screen.getByRole("link", { name: /Story u/ })).toHaveAttribute("rel", "nofollow");
    expect(screen.getByRole("link", { name: /Story v/ })).not.toHaveAttribute("rel");
  });
});
