import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { FollowUps } from "@/components/FollowUps";
import type { FollowUpRef } from "@/lib/api";

const ref = (id: string, title: string, first_seen_at: string, source_count: number | null): FollowUpRef => ({ id, title, first_seen_at, source_count });
const side = (label: string) => within(screen.getByRole("heading", { name: label }).parentElement!);

describe("FollowUps — earlier and later records, linked record to record", () => {
  it("lists each side with a link to the record, its IST date and its outlet count", () => {
    render(<FollowUps followUps={{
      // 20:00 UTC on the 20th is the 21st in IST: the date is the newsroom's.
      earlier: [ref("e0", "High Court disqualifies the MLA", "2026-09-20T20:00:00Z", 3)],
      later: [
        ref("e2", "Supreme Court upholds the disqualification", "2026-09-27T04:00:00Z", 1),
        ref("e3", "By-election notified", "2026-09-28T05:00:00Z", null),
      ],
    }} />);

    const earlier = side("Earlier in this story");
    expect(earlier.getByRole("link", { name: "High Court disqualifies the MLA" })).toHaveAttribute("href", "/story/e0");
    expect(earlier.getByText("21 Sept · 3 outlets")).toHaveClass("p-count"); // the mono provenance voice
    expect(earlier.queryByRole("link", { name: /Supreme Court/ })).toBeNull();

    const later = side("Later in this story");
    expect(later.getByRole("link", { name: "Supreme Court upholds the disqualification" })).toHaveAttribute("href", "/story/e2");
    expect(later.getByText("27 Sept · 1 outlet")).toBeInTheDocument();
    // No count on the payload: the date alone, never "null outlets".
    expect(later.getByRole("link", { name: "By-election notified" })).toHaveAttribute("href", "/story/e3");
    expect(later.getByText("28 Sept")).toBeInTheDocument();
  });

  // A one-outlet record asks not to be indexed (lib/seo.followRel), so the link spends no follow on it.
  it("marks a one-outlet record's link nofollow, plain otherwise or when the count is unknown", () => {
    render(<FollowUps followUps={{
      earlier: [ref("a", "One outlet", "2026-09-20T06:00:00Z", 1), ref("b", "Two outlets", "2026-09-21T06:00:00Z", 2)],
      later: [ref("c", "Not counted", "2026-09-22T06:00:00Z", null)],
    }} />);
    expect(screen.getByRole("link", { name: "One outlet" })).toHaveAttribute("rel", "nofollow");
    expect(screen.getByRole("link", { name: "Two outlets" })).not.toHaveAttribute("rel");
    expect(screen.getByRole("link", { name: "Not counted" })).not.toHaveAttribute("rel");
  });

  it("prints only the side that has records", () => {
    render(<FollowUps followUps={{ earlier: [], later: [ref("e2", "Supreme Court upholds it", "2026-09-27T04:00:00Z", 4)] }} />);
    expect(screen.getByRole("heading", { name: "Later in this story" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Earlier in this story" })).toBeNull();
  });

  it("renders nothing when both sides are empty or the payload predates the field", () => {
    expect(render(<FollowUps followUps={{ earlier: [], later: [] }} />).container.innerHTML).toBe("");
    expect(render(<FollowUps followUps={undefined} />).container.innerHTML).toBe("");
  });
});
