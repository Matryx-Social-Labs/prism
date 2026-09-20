import { MARK_BAND, MARK_BOX, MARK_TRIANGLE, bandSegments } from "@/lib/mark";
import { OG_COLORS, OG_DISPLAY, OG_MONO, displayStack } from "@/lib/ogFonts";

/** The mark as PrismMark draws it, for Satori: a solid triangle on the spectrum bar. */
export function PrismMarkSvg({ size, ink }: { size: number; ink: string }) {
  // Same geometry as components/PrismMark (lib/mark.ts); inline for next/og.
  return (
    <svg width={size} height={size} viewBox={`0 0 ${MARK_BOX} ${MARK_BOX}`} fill="none">
      <path d={MARK_TRIANGLE} fill={ink} />
      {bandSegments().map((s) => (
        <rect key={s.color} x={s.x} y={MARK_BAND.y} width={s.width} height={MARK_BAND.height} fill={s.color} />
      ))}
    </svg>
  );
}

/**
 * The share card, 1200 × 630: the chart's row grammar at poster scale
 * (design 12-share-card). The wordmark and the tagline on top; the count in
 * Teko beside the headline in Hind with its grid label in mono beneath; a
 * rule and the provenance line at the foot. Monochrome: the only colour on a
 * card is the mark's own spectrum, and that is the mark, not a lens.
 */
export function OgCard({ count, countLabel, headline, grid, foot, host }: { count: number | string; countLabel: string; headline: string; grid: string[]; foot: string; host: string }) {
  const c = OG_COLORS;
  return (
    <div style={{ height: "100%", width: "100%", display: "flex", flexDirection: "column", background: c.ground, color: c.ink, padding: "48px 56px", fontFamily: displayStack(headline) }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <PrismMarkSvg size={30} ink={c.ink} />
          <span style={{ fontFamily: OG_DISPLAY, fontSize: 40, letterSpacing: 2, lineHeight: 1 }}>PRISM</span>
        </div>
        <span style={{ fontFamily: OG_MONO, fontSize: 16, color: c.inkMuted }}>Follow the story, not the headlines.</span>
      </div>
      <div style={{ display: "flex", gap: 32, paddingTop: 36, flex: 1 }}>
        <span style={{ fontFamily: OG_DISPLAY, fontSize: 150, lineHeight: 0.85, letterSpacing: -3, width: 140, display: "flex", justifyContent: "flex-end" }}>{count}</span>
        <div style={{ display: "flex", flexDirection: "column", flex: 1 }}>
          <span style={{ fontFamily: OG_MONO, fontSize: 16, color: c.inkFaint, textTransform: "uppercase", letterSpacing: 1 }}>{countLabel}</span>
          <span style={{ marginTop: 12, fontSize: 46, lineHeight: 1.15, fontWeight: 500, maxWidth: 900 }}>{headline}</span>
          <div style={{ display: "flex", gap: 16, marginTop: 16, fontFamily: OG_MONO, fontSize: 16, color: c.inkFaint, textTransform: "uppercase", letterSpacing: 1 }}>
            {grid.map((g, i) => <span key={i}>{g}</span>)}
          </div>
        </div>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", borderTop: `1px solid ${c.line}`, paddingTop: 18, fontFamily: OG_MONO, fontSize: 16, color: c.inkMuted, textTransform: "uppercase", letterSpacing: 1 }}>
        <span>{foot}</span><span>{host}</span>
      </div>
    </div>
  );
}
