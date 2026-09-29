import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RelatedRoutes } from "@/components/RelatedRoutes";

describe("RelatedRoutes — different stories, said beside the route", () => {
  it("names the relation in the record's terms and links to the other route", () => {
    render(<RelatedRoutes related={[
      { slug: "neet", label: "The NEET protests", developments: 25, source_count: 48, velocity: 2, last_updated_at: "2026-09-15T06:00:00Z", shared_cast: ["Dharmendra Pradhan"], causal: true },
      { slug: "caste", label: "The caste survey", developments: 7, source_count: 9, velocity: 0, last_updated_at: "2026-09-04T06:00:00Z", shared_cast: ["Siddaramaiah", "Congress"], causal: false },
    ]} />);
    expect(screen.getByRole("link", { name: "The NEET protests" })).toHaveAttribute("href", "/trending/neet");
    expect(screen.getByText(/linked by a causal note · shares Dharmendra Pradhan · 25 related events/)).toBeInTheDocument();
    expect(screen.getByText("moving")).toBeInTheDocument();
    expect(screen.getByText(/shares Siddaramaiah · Congress · 7 related events · quiet since/)).toBeInTheDocument();
  });
  // A provisional grouping asks not to be indexed, so the page spends no follow
  // link on it; the status is the page's own story's (one switch for every story).
  it("marks the links nofollow while stories are provisional, plain once verified or unknown", () => {
    const one = [{ slug: "neet", label: "The NEET protests", developments: 2, source_count: 4, velocity: 0, last_updated_at: null, shared_cast: [], causal: true }];
    const rel = (indexable?: boolean) => {
      const { unmount } = render(<RelatedRoutes related={one} indexable={indexable} />);
      const value = screen.getByRole("link", { name: "The NEET protests" }).getAttribute("rel");
      unmount();
      return value;
    };
    expect(rel(false)).toBe("nofollow");
    expect(rel(true)).toBeNull();
    expect(rel(undefined)).toBeNull();
  });
  it("renders nothing when there are none", () => {
    expect(render(<RelatedRoutes related={[]} />).container.innerHTML).toBe("");
  });
});
