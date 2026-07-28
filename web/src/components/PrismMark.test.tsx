import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { PrismMark } from "@/components/PrismMark";

describe("the brand mark", () => {
  // REGRESSION: the design defines the spectrum gradient once per page and lets
  // every later mark reference it by a shared id. Ported literally, two marks on
  // one page (header + footer) emit duplicate ids, and unmounting the first
  // leaves the second's base bar unpainted — a logo that loses its spectrum on
  // navigation. Each instance must own its gradient.
  it("gives every instance its own gradient, so a second mark still paints", () => {
    const { container } = render(
      <>
        <PrismMark />
        <PrismMark size={14} />
      </>,
    );
    const ids = [...container.querySelectorAll("linearGradient")].map((g) => g.id);
    expect(ids).toHaveLength(2);
    expect(new Set(ids).size).toBe(2);

    // ...and each rect actually points at its own instance's gradient.
    const rects = [...container.querySelectorAll("rect")];
    expect(rects.map((r) => r.getAttribute("fill"))).toEqual(ids.map((id) => `url(#${id})`));
  });

  it("keeps the mark's 24:22 ratio at every size the design uses", () => {
    for (const [size, height] of [
      [14, 13],
      [18, 17],
      [21, 19],
      [22, 20],
    ]) {
      const { container } = render(<PrismMark size={size} />);
      const svg = container.querySelector("svg")!;
      expect([svg.getAttribute("width"), svg.getAttribute("height")]).toEqual([
        String(size),
        String(height),
      ]);
    }
  });

  it("takes its ink from currentColor so it reverses on charcoal", () => {
    const { container } = render(<PrismMark />);
    const tri = container.querySelector("path")!;
    expect(tri.getAttribute("fill")).toBe("currentColor");
    expect(tri.getAttribute("stroke")).toBe("currentColor");
  });
});
