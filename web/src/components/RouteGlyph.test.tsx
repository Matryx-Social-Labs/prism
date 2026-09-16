import { describe, expect, it } from "vitest";
import { render } from "@testing-library/react";
import { RouteGlyph } from "@/components/RouteGlyph";

const d = (day: number) => new Date(Date.UTC(2026, 7, 27 + day)).toISOString();
const node = (id: string, parent_id: string | null, day: number, off_spine = false) => ({ id, parent_id, off_spine, occurred_at: d(day) });

describe("RouteGlyph — the map in one line", () => {
  it("draws the main line's stations, a branch stub with its stations, a satellite stub, the latest filled", () => {
    // r → a → b is the main line; x off r is a branch of one; s is a satellite.
    const route = { root_id: "r", nodes: [node("r", null, 0), node("a", "r", 1), node("b", "a", 2), node("x", "r", 1), node("s", "r", 2, true)] };
    const { container } = render(<RouteGlyph route={route} />);
    expect(container.querySelectorAll("line")).toHaveLength(1);
    expect(container.querySelectorAll("circle:not([r='2.5'])")).toHaveLength(3);
    expect(container.querySelectorAll(".rg-branch")).toHaveLength(1);
    expect(container.querySelectorAll("circle[r='2.5']")).toHaveLength(1);
    expect(container.querySelectorAll(".rg-sat")).toHaveLength(1);
    expect(container.querySelectorAll(".rg-here")).toHaveLength(1);
  });
  it("renders nothing without a route", () => {
    expect(render(<RouteGlyph route={null} />).container.innerHTML).toBe("");
  });
});
