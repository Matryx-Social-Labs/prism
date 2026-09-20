/**
 * The Prism mark's geometry, defined once (design/logo/build.py draws the same
 * numbers for the exports).
 *
 * A 24×24 box. The prism is an equilateral triangle, FILL ONLY — the old mark
 * stroked it at 1.5, which put every edge on a fraction and clipped the base
 * below the box. Base 20 wide (x 2…22) at y 19.5; apex at 19.5 − 20·√3/2 = 2.18.
 * The spectrum is a band ATTACHED to the base — its top edge is the base line,
 * exactly the base's width, 2.75 tall: one shape, prism standing on its
 * spectrum (founder, 2026-09-20: a gap read as a split icon). The old band was
 * painted over the triangle's bottom two units and ran wider than the triangle
 * there, so its ends stuck out past the slanted sides. The band is a
 * continuous spectrum, red → amber → cyan → violet (founder: a spectrum, not
 * blocks), with the stops at the design's four hues.
 */
export const MARK_BOX = 24;
export const MARK_TRIANGLE = "M12 2.18 L22 19.5 L2 19.5 Z";
/** The band's top IS the triangle's base line — no gap. */
export const MARK_BASE_Y = 19.5;
export const MARK_BAND = { x: 2, y: MARK_BASE_Y, width: 20, height: 2.75 };
export const SPECTRUM = ["#ef4444", "#f59e0b", "#06b6d4", "#8b5cf6"] as const;

/** Gradient stops, evenly spaced across the band: 0, 1/3, 2/3, 1. */
export const SPECTRUM_STOPS: { offset: number; color: string }[] = SPECTRUM.map((color, i) => ({ offset: i / (SPECTRUM.length - 1), color }));
