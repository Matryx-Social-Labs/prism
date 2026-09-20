import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { PrismMark } from "@/components/PrismMark";
import { MARK_BAND, MARK_TRIANGLE, SPECTRUM } from "@/lib/mark";

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

  it("puts the spectrum below the base, exactly as wide as the base, in four crisp segments", () => {
    const { container } = render(<PrismMark size={24} />);
    const rects = [...container.querySelectorAll("rect")];
    expect(rects).toHaveLength(SPECTRUM.length);
    expect(rects.map((r) => r.getAttribute("fill"))).toEqual([...SPECTRUM]);
    const xs = rects.map((r) => Number(r.getAttribute("x")));
    const ws = rects.map((r) => Number(r.getAttribute("width")));
    // Base runs x 2…22; the band covers exactly that, contiguous, no overhang.
    expect(xs[0]).toBe(2);
    expect(xs[xs.length - 1] + ws[ws.length - 1]).toBe(22);
    for (let i = 1; i < xs.length; i++) expect(xs[i]).toBeCloseTo(xs[i - 1] + ws[i - 1], 6);
    // Below the base (y 19), never over it.
    expect(MARK_BAND.y).toBeGreaterThan(19);
    expect(MARK_BAND.y + MARK_BAND.height).toBeLessThanOrEqual(24);
  });

  it("is square at every size the design uses", () => {
    for (const size of [14, 18, 21, 22, 32]) {
      const { container } = render(<PrismMark size={size} />);
      const svg = container.querySelector("svg")!;
      expect([svg.getAttribute("width"), svg.getAttribute("height")]).toEqual([String(size), String(size)]);
    }
  });
});
