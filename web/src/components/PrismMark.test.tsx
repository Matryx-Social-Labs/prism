import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PrismMark } from "@/components/PrismMark";
import { MARK_BAND, MARK_BASE_Y, MARK_TRIANGLE, SPECTRUM } from "@/lib/mark";

/**
 * The mark's geometry, pinned. The old mark stroked the triangle at 1.5 (edges
 * on fractions, base clipped below the box) and painted a gradient band OVER
 * the triangle's bottom two units, wider than the triangle there, so at any
 * zoom the band's ends stuck out past the slanted sides (founder, 2026-09-20).
 */
describe("PrismMark", () => {
  it("is a fill-only triangle with no stroke, inside the box", () => {
    const { container } = render(<PrismMark size={24} />);
    const tri = container.querySelector("path")!;
    expect(tri.getAttribute("fill")).toBe("currentColor");
    expect(tri.getAttribute("stroke")).toBeNull();
    expect(tri.getAttribute("d")).toBe(MARK_TRIANGLE);
  });

  it("stands the prism ON its spectrum: the band's top is the base line, no gap, exactly the base's width", () => {
    const { container } = render(<><PrismMark size={24} /><PrismMark size={24} /></>);
    const rects = [...container.querySelectorAll("rect")];
    expect(rects).toHaveLength(2);
    // The triangle's base line, read from the path itself.
    const baseY = Number(/L22 ([\d.]+) L2/.exec(MARK_TRIANGLE)![1]);
    expect(baseY).toBe(MARK_BASE_Y);
    for (const r of rects) {
      expect([Number(r.getAttribute("x")), Number(r.getAttribute("width"))]).toEqual([2, 20]);
      expect(Number(r.getAttribute("y"))).toBe(baseY);
      expect(Number(r.getAttribute("y")) + Number(r.getAttribute("height"))).toBeLessThanOrEqual(24);
    }
    // One gradient per instance, four stops in the design's hues.
    const ids = [...container.querySelectorAll("linearGradient")].map((g) => g.id);
    expect(new Set(ids).size).toBe(2);
    expect(rects.map((r) => r.getAttribute("fill"))).toEqual(ids.map((id) => `url(#${id})`));
    const stops = [...container.querySelectorAll("linearGradient")][0].querySelectorAll("stop");
    expect([...stops].map((s) => s.getAttribute("stop-color"))).toEqual([...SPECTRUM]);
  });

  it("is square at every size the design uses", () => {
    for (const size of [14, 18, 21, 22, 32]) {
      const { container } = render(<PrismMark size={size} />);
      const svg = container.querySelector("svg")!;
      expect([svg.getAttribute("width"), svg.getAttribute("height")]).toEqual([String(size), String(size)]);
    }
  });
});
