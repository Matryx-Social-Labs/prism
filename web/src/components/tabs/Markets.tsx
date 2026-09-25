import Link from "next/link";
import type { MarketDigest as Digest } from "@/lib/api";
import { istTime } from "@/lib/dateline";

// The markets pieces of the Watchlist and You tabs (Design System v2 ·
// record/TickerChip, structure/MarketDigest + MoversList). The Markets lens is
// speaking in each of them, so its hue marks them; nothing else here is coloured.

const TICKER_STYLE: React.CSSProperties = {
  height: 26,
  fontSize: 12,
  textDecoration: "none",
  borderColor: "color-mix(in srgb, var(--lens-markets) 45%, var(--line))",
  background: "var(--lens-markets-soft)",
  color: "var(--lens-markets)",
};

/** A ticker in mono on the Markets tint; a link when it has somewhere to go. */
export function TickerChip({ symbol, href }: { symbol: string; href?: string }) {
  if (!href) return <span className="p-tag-mono" style={TICKER_STYLE}>{symbol}</span>;
  return <Link href={href} className="p-tag-mono" style={TICKER_STYLE}>{symbol}</Link>;
}

/** The day's markets reading, as the API wrote it: headline, the first paragraph,
 *  and what it was written from — a count and a time, both from the payload. */
export function MarketDigest({ digest }: { digest: Digest }) {
  const n = digest.event_ids.length;
  const prov = [`written from ${n} ${n === 1 ? "story" : "stories"}`, digest.generated_at ? `updated ${istTime(digest.generated_at)} IST` : null].filter(Boolean).join(" · ");
  const lede = digest.narrative.split(/\n{2,}/)[0];
  return (
    <article
      className="grid gap-2.5 p-5"
      style={{ background: "var(--lens-markets-soft)", borderTop: "3px solid var(--lens-markets)", borderRadius: "0 0 var(--r-lg) var(--r-lg)", color: "var(--ink)" }}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="p-lensdot p-l-markets"><i />Markets read</span>
        <span className="p-count">{prov}</span>
      </div>
      <h2 className="text-balance" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>{digest.headline}</h2>
      {/* The rest of the reading is one tap away on Market Pulse. */}
      {lede && <p className="line-clamp-4" style={{ font: "var(--t-body)" }}>{lede}</p>}
    </article>
  );
}

/** Each mover: its ticker, then the digest's one line on why. */
export function MoversList({ movers, tickerHref }: { movers: Digest["movers"]; tickerHref: (t: string) => string }) {
  return (
    <ul className="grid">
      {movers.map((m) => (
        <li key={m.ticker} className="grid grid-cols-[110px_minmax(0,1fr)] items-baseline gap-3 border-t py-2.5" style={{ borderColor: "var(--line)" }}>
          <span className="justify-self-start"><TickerChip symbol={m.ticker} href={tickerHref(m.ticker)} /></span>
          <span style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>{m.note}</span>
        </li>
      ))}
    </ul>
  );
}
