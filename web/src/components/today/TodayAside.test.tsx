import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import type { TrendingStory } from "@/lib/api";
import { TodayAside } from "@/components/today/TodayAside";

const story = (slug: string, boundary_status: "provisional" | "verified") =>
  ({ slug, label: `Story ${slug}`, boundary_status, developments: 3, source_count: 4, last_updated_at: null, outlets: [] }) as unknown as TrendingStory;

// /feed is the biggest hub a crawler reaches; a provisional grouping is noindex,
// so following it is a paid render Google then drops (audit 2026-09-29).
describe("TodayAside", () => {
  it("follows a verified story and not a provisional grouping", () => {
    render(<TodayAside developing={[story("held", "provisional"), story("done", "verified")]} />);
    const links = screen.getAllByRole("link", { hidden: true });
    expect(links.find((a) => a.getAttribute("href") === "/trending/held")).toHaveAttribute("rel", "nofollow");
    expect(links.find((a) => a.getAttribute("href") === "/trending/done")).not.toHaveAttribute("rel");
  });
});
