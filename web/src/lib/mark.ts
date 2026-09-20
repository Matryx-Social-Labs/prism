/**
 * The Prism mark's geometry, defined once (design/logo/build.py draws the same
 * numbers for the exports).
 *
 * A 24×24 box. The prism is an equilateral triangle, FILL ONLY — the old mark
 * stroked it at 1.5, which put every edge on a fraction and clipped the base
 * below the box. Base 20 wide (x 2…22) at y 19; apex at 19 − 20·√3/2 = 1.68.
 * The spectrum is a band BELOW the base, exactly the base's width, with a
 * 1.25 gap: the light leaves the prism and lands on the ground. The old band
 * was painted over the triangle's bottom two units and ran wider than the
 * triangle there, so its ends stuck out past the slanted sides. Four crisp
 * segments in the design's four hues (the coverage bar's slot order, DESIGN.md
 * § Colour), not a gradient — at 21px a gradient is mud.
 */
export const MARK_BOX = 24;
export const MARK_TRIANGLE = "M12 1.68 L22 19 L2 19 Z";
export const MARK_BAND = { x: 2, y: 20.25, width: 20, height: 2.75 };
export const SPECTRUM = ["#ef4444", "#f59e0b", "#06b6d4", "#8b5cf6"] as const;

/** The four band segments, left → right, as rects. */
export function bandSegments(): { x: number; width: number; color: string }[] {
  const w = MARK_BAND.width / SPECTRUM.length;
  return SPECTRUM.map((color, i) => ({ x: MARK_BAND.x + i * w, width: w, color }));
}
