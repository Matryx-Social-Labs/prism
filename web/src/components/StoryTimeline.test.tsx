/**
 * A story's records by day, in the order they were first reported (the API
 * sorts on first_published_at): the gutter prints the day where it changes and
 * every record's first-report time on the newsroom (IST) clock. Before, each
 * row printed occurred_at's bare day, and a backlog's records read in the order
 * Prism processed them (Flydubai, 2026-10-01).
 */
import { describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { StoryTimeline } from "@/components/StoryTimeline";
import type { StoryDevelopment } from "@/lib/api";

const dev = (id: string, title: string, first_published_at: string | null, occurred_at: string | null = null): StoryDevelopment => ({
  id, title, sector: "civic", occurred_at, first_published_at, image_url: null, is_current: false, why: null, source_count: 2,
});

const devs = [
  dev("a", "Passengers subdue the attacker", "2026-09-30T09:21:00Z"),
  dev("b", "Captain saves the flight", "2026-09-30T13:33:00Z"),
  dev("c", "Modi praises the pilot", "2026-09-30T20:42:00Z"), // 02:12 IST on 1 Oct
];

function gutter(title: string) {
  return within(screen.getByText(title).closest("li")!).getByRole("time");
}

describe.each(["related", "timeline"] as const)("StoryTimeline (%s)", (mode) => {
  it("prints the day where it changes and each record's first-report time", () => {
    render(<StoryTimeline story={{ developments: devs, cast: [] }} mode={mode} />);
    expect(gutter("Passengers subdue the attacker")).toHaveTextContent(/^30 SEPT14:51$/);
    expect(gutter("Captain saves the flight")).toHaveTextContent(/^19:03$/);
    expect(gutter("Modi praises the pilot")).toHaveTextContent(/^1 OCT02:12$/);
    expect(gutter("Modi praises the pilot")).toHaveAttribute("dateTime", "2026-09-30T20:42:00Z");
  });

  it("falls back to the day alone on an older payload with no first-report time", () => {
    render(<StoryTimeline story={{ developments: [dev("a", "One", null, "2026-09-29"), dev("b", "Two", null, "2026-09-30")], cast: [] }} mode={mode} />);
    expect(gutter("One")).toHaveTextContent(/^29 SEPT$/);
    expect(gutter("Two")).toHaveTextContent(/^30 SEPT$/);
  });
});

/**
 * Facets: what kind of development each record is in its story (the judge's
 * fixed list). On the Flydubai story: event 13 · investigation 12 · response 9 ·
 * people 19 · reactions 42 · politics 7 — the chips filter the list to one kind.
 */
describe.each(["related", "timeline"] as const)("StoryTimeline facets (%s)", (mode) => {
  const faceted = [
    { ...dev("a", "Flight diverted to Saudi Arabia", "2026-09-30T07:33:00Z"), facet: "event" },
    { ...dev("b", "UAE opens a probe", "2026-10-01T04:00:00Z"), facet: "investigation" },
    { ...dev("c", "Modi praises the pilot", "2026-10-01T02:12:00Z"), facet: "reactions" },
    { ...dev("d", "Trump praises the pilot", "2026-10-01T02:03:00Z"), facet: "reactions" },
  ];

  it("counts each kind and filters the list to the one chosen", async () => {
    const { default: userEvent } = await import("@testing-library/user-event");
    render(<StoryTimeline story={{ developments: faceted, cast: [] }} mode={mode} />);
    expect(screen.getByRole("button", { name: "All 4" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByRole("button", { name: "Reactions 2" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reactions 2" }));
    expect(screen.getByRole("button", { name: "Reactions 2" })).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("Modi praises the pilot")).toBeInTheDocument();
    expect(screen.queryByText("UAE opens a probe")).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "All 4" }));
    expect(screen.getByText("UAE opens a probe")).toBeInTheDocument();
  });

  it("shows no chips when the records carry no facet or only one kind", () => {
    render(<StoryTimeline story={{ developments: devs, cast: [] }} mode={mode} />);
    expect(screen.queryByRole("button", { name: /^All / })).not.toBeInTheDocument();
  });
});
