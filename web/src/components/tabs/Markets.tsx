import Link from "next/link";

// The ticker chip of Market Pulse and the Watchlist and You tabs (Design System
// v2 · record/TickerChip). The Markets lens is speaking wherever a ticker is, so
// its hue marks the chip; nothing else here is coloured.

const TICKER_STYLE: React.CSSProperties = {
  height: 26,
  fontSize: 12,
  textDecoration: "none",
  borderColor: "color-mix(in srgb, var(--lens-markets) 45%, var(--line))",
  background: "var(--lens-markets-soft)",
  color: "var(--lens-markets)",
};

/** A ticker in mono on the Markets tint; a link when it has somewhere to go (with a
 *  ≥44px tap area, .p-hit). With `onToggle` it carries its Follow / Following button. */
export function TickerChip({ symbol, href, following, onToggle, busy }: { symbol: string; href?: string; following?: boolean; onToggle?: () => void; busy?: boolean }) {
  const chip = href
    ? <Link href={href} className="p-tag-mono p-hit" style={TICKER_STYLE}>{symbol}</Link>
    : <span className="p-tag-mono" style={TICKER_STYLE}>{symbol}</span>;
  if (!onToggle) return chip;
  return (
    <span className="inline-flex items-center gap-2">
      {chip}
      <button type="button" className="p-btn p-btn--sm p-btn--secondary p-hit" aria-pressed={Boolean(following)} onClick={onToggle} disabled={busy} style={{ minHeight: 32 }}>
        {following ? `Following ${symbol}` : `Follow ${symbol}`}
      </button>
    </span>
  );
}
