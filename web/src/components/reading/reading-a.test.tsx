import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { attentionDays } from "@/components/Attention";
import { StoryArc } from "@/components/reading/StoryArc";
import { PulseRail } from "@/components/reading/PulseRail";
import type { StoryDevelopment, TrendingStoryDetail } from "@/lib/api";

const dev = (id: string, day: string, title: string, source_count?: number, is_current = false): StoryDevelopment => ({ id, title, sector: "politics", occurred_at: day, image_url: null, is_current, why: null, source_count });

describe("Sources per day — uncounted days are never zero", () => {
  it("sums each day's sources, and leaves a day with no count as not counted", () => {
    const days = attentionDays([dev("a", "2026-09-19", "A", 3), dev("b", "2026-09-19", "B", 2), dev("c", "2026-09-21", "C", 4), dev("d", "2026-09-22", "D")]);
    expect(days).toEqual([
      { day: "2026-09-19", n: 5 },
      { day: "2026-09-20", n: null }, // no development that day: not counted, not 0
      { day: "2026-09-21", n: 4 },
      { day: "2026-09-22", n: null }, // a development without a count leaves its day uncounted
    ]);
  });
});

function story(over: Partial<TrendingStoryDetail> = {}): TrendingStoryDetail {
  return {
    slug: "s", canonical_slug: "s", label: "Jamui harassment case", photos: [], outlets: [], cast: [], sector: "politics",
    source_count: 4, velocity: 1, status: "active", timeline_cast: [], branches: null, related: [], boundary_status: "provisional",
    developments: [dev("a", "2026-09-19", "First report", 3, true), dev("b", "2026-09-22", "Latest report", 1)],
    ...over,
  };
}

describe("The story arc — a provisional grouping", () => {
  it("says it is provisional, implies no order, marks no development as here, and ends on the latest record", () => {
    render(<StoryArc s={story()} />);
    expect(screen.getAllByText("Provisional grouping").length).toBeGreaterThan(0);
    expect(screen.getByText(/No chronology implied/)).toBeInTheDocument();
    expect(screen.queryByText(/You are here/i)).toBeNull();
    const latest = screen.getByRole("region", { name: "The latest record" });
    expect(latest.querySelector("a")).toHaveAttribute("href", "/story/b");
    expect(screen.queryByText("How it unfolded")).toBeNull();
  });
});

describe("Market Pulse — the rail signed out", () => {
  it("says what following does and signs in back to the pulse", () => {
    render(<PulseRail session={null} named={[]} />);
    expect(screen.getByText(/Follow a ticker to see its stories/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Sign in" })).toHaveAttribute("href", "/signin?next=/pulse");
  });
});
