"use client";

import { useId } from "react";
import { MARK_BAND, MARK_BOX, MARK_TRIANGLE, SPECTRUM_STOPS } from "@/lib/mark";

// The brand glyph: a prism standing over its spectrum. Geometry in lib/mark.ts,
// shared with the favicon, the share card and the PNG exports, so the tab, the
// masthead and a WhatsApp preview never disagree. The triangle inherits
// `currentColor` (ink on ivory, ivory on charcoal); the band is the one
// coloured element and the only spectrum in the system (DESIGN.md § Colour).
// The gradient id is per instance: two marks on a page (header + footer) must
// not share one, or the second loses its paint when the first unmounts.
export function PrismMark({ size = 21 }: { size?: number }) {
  const gid = `prism-spectrum-${useId().replace(/:/g, "")}`;
  return (
    <svg width={size} height={size} viewBox={`0 0 ${MARK_BOX} ${MARK_BOX}`} fill="none" aria-hidden="true" style={{ flex: "none" }} shapeRendering="geometricPrecision">
      <path d={MARK_TRIANGLE} fill="currentColor" />
      <rect x={MARK_BAND.x} y={MARK_BAND.y} width={MARK_BAND.width} height={MARK_BAND.height} fill={`url(#${gid})`} />
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="0">
          {SPECTRUM_STOPS.map((s) => <stop key={s.color} offset={s.offset} stopColor={s.color} />)}
        </linearGradient>
      </defs>
    </svg>
  );
}
