import { OG_COLORS, OG_DISPLAY, OG_MONO, displayStack } from "@/lib/ogFonts";

/** The mark as PrismMark draws it, for Satori: a solid triangle on the spectrum bar. */
export function PrismMarkSvg({ size, ink }: { size: number; ink: string }) {
  return (
    <svg width={size} height={Math.round((size * 22) / 24)} viewBox="0 0 24 22" fill="none">
      <path d="M12 1 L23 21 L1 21 Z" fill={ink} stroke={ink} strokeWidth={1.5} strokeLinejoin="round" />
      <rect x="1" y="19" width="22" height="3" fill="url(#sp)" />
      <defs>
        <linearGradient id="sp" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#ef4444" /><stop offset="35%" stopColor="#f59e0b" /><stop offset="70%" stopColor="#06b6d4" /><stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
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
        <span style={{ fontFamily: OG_MONO, fontSize: 16, color: c.inkMuted }}>One story. Every perspective.</span>
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
