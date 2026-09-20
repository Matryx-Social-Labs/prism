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
 * triangle there, so its ends stuck out past the slanted sides. The band is a
 * continuous spectrum, red → amber → cyan → violet (founder: a spectrum, not
 * blocks), with the stops at the design's four hues.
 */
export const MARK_BOX = 24;
export const MARK_TRIANGLE = "M12 1.68 L22 19 L2 19 Z";
export const MARK_BAND = { x: 2, y: 20.25, width: 20, height: 2.75 };
export const SPECTRUM = ["#ef4444", "#f59e0b", "#06b6d4", "#8b5cf6"] as const;

/** Gradient stops, evenly spaced across the band: 0, 1/3, 2/3, 1. */
export const SPECTRUM_STOPS: { offset: number; color: string }[] = SPECTRUM.map((color, i) => ({ offset: i / (SPECTRUM.length - 1), color }));
