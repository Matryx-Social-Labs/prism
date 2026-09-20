// The brand glyph: a prism standing over its spectrum. Geometry in lib/mark.ts,
// shared with the favicon, the share card and the PNG exports, so the tab, the
// masthead and a WhatsApp preview never disagree. The triangle inherits
// `currentColor` (ink on ivory, ivory on charcoal); the band is the one
// coloured element and the only spectrum in the system (DESIGN.md § Colour).
import { MARK_BAND, MARK_BOX, MARK_TRIANGLE, bandSegments } from "@/lib/mark";

export function PrismMark({ size = 21 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox={`0 0 ${MARK_BOX} ${MARK_BOX}`} fill="none" aria-hidden="true" style={{ flex: "none" }} shapeRendering="geometricPrecision">
      <path d={MARK_TRIANGLE} fill="currentColor" />
      {bandSegments().map((s) => (
        <rect key={s.color} x={s.x} y={MARK_BAND.y} width={s.width} height={MARK_BAND.height} fill={s.color} />
      ))}
    </svg>
  );
}
