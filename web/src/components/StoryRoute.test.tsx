/**
 * The route section on a record page. A story the judge built (verified) carries
 * no branch tree: that was the Leiden partition's. Before 0.0.130.0 the section
 * returned nothing for it, so every live story would have vanished from its
 * records' pages; it now prints the story's developments by day, this one marked.
 */
import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import type { StoryDevelopment, TrendingStoryDetail } from "@/lib/api";

const fetchTrendingStory = vi.fn();
vi.mock("@/lib/api", async (orig) => ({ ...(await orig<object>()), fetchTrendingStory: (...a: unknown[]) => fetchTrendingStory(...a) }));

import { StoryRoute } from "@/components/StoryRoute";

const dev = (id: string, title: string, at: string): StoryDevelopment => ({
  id, title, sector: "civic", occurred_at: null, first_published_at: at, image_url: null, is_current: id === "a", why: null,
  source_count: 3, facet: id === "a" ? "event" : "investigation",
});

const story = (over: Partial<TrendingStoryDetail> = {}): TrendingStoryDetail => ({
  slug: "flydubai-1", canonical_slug: "flydubai-1", label: "Flydubai flight", cast: [], sector: "civic", source_count: 9,
  velocity: 2, status: "active", boundary_status: "verified", branches: null, related: [], timeline_cast: [],
  developments: [dev("a", "Flight lands in Saudi Arabia", "2026-09-30T09:00:00Z"), dev("b", "UAE opens probe", "2026-09-30T12:00:00Z")],
  ...over,
} as TrendingStoryDetail);

afterEach(() => fetchTrendingStory.mockReset());

describe("StoryRoute", () => {
  it("prints a verified story without a branch tree as its timeline, this record marked", async () => {
    fetchTrendingStory.mockResolvedValue(story());
    render(<StoryRoute slug="flydubai-1" currentId="b" />);
    expect(await screen.findByText("UAE opens probe")).toBeInTheDocument();
    expect(screen.getByText("You are here")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Flight lands in Saudi Arabia" })).toHaveAttribute("href", "/story/a");
    expect(screen.getByRole("link", { name: /Open this story/ })).toHaveAttribute("href", "/trending/flydubai-1");
  });

  it("keeps a provisional group as related coverage, no order claimed", async () => {
    fetchTrendingStory.mockResolvedValue(story({ boundary_status: "provisional" }));
    render(<StoryRoute slug="flydubai-1" currentId="b" />);
    expect(await screen.findByRole("link", { name: /Open this coverage group/ })).toBeInTheDocument();
  });
});
