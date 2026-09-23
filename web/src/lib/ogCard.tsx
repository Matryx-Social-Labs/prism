import { langName } from "@/lib/languages";
import { MARK_BAND, MARK_BOX, MARK_TRIANGLE, SPECTRUM_STOPS } from "@/lib/mark";
import { OG_COLORS, OG_DISPLAY, OG_MONO, OG_SANS, bodyStack, displayStack } from "@/lib/ogFonts";

/** The mark as PrismMark draws it, for Satori: a solid triangle on the spectrum bar. */
export function PrismMarkSvg({ size, ink }: { size: number; ink: string }) {
  return (
    <svg width={size} height={size} viewBox={`0 0 ${MARK_BOX} ${MARK_BOX}`} fill="none">
      <path d={MARK_TRIANGLE} fill={ink} />
      <rect x={MARK_BAND.x} y={MARK_BAND.y} width={MARK_BAND.width} height={MARK_BAND.height} fill="url(#sp)" />
      <defs>
        <linearGradient id="sp" x1="0" y1="0" x2="1" y2="0">
          {SPECTRUM_STOPS.map((s) => <stop key={s.color} offset={s.offset} stopColor={s.color} />)}
        </linearGradient>
      </defs>
    </svg>
  );
}

const c = OG_COLORS;
const W = 1200;
const H = 630;
const PAD = 60;

/** Top row: the mark and the wordmark; the host on the right. Same on every card. */
function Masthead({ host, kicker }: { host: string; kicker?: string }) {
  return (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <PrismMarkSvg size={34} ink={c.ink} />
        <span style={{ fontFamily: OG_DISPLAY, fontSize: 34, fontWeight: 700, letterSpacing: -0.5, lineHeight: 1 }}>Prism</span>
        {kicker && <span style={{ marginLeft: 8, fontFamily: OG_MONO, fontSize: 16, color: c.inkFaint, letterSpacing: 1, textTransform: "uppercase" }}>{kicker}</span>}
      </div>
      <span style={{ fontFamily: OG_MONO, fontSize: 16, color: c.inkFaint }}>{host}</span>
    </div>
  );
}

/** The coverage bar at poster scale: segments by outlet origin, the count beside it. */
export function CoverageBarSvg({ counts, width = 260, height = 10 }: { counts: { national?: number; intl?: number; regional?: number; wire?: number }; width?: number; height?: number }) {
  const order: (keyof typeof c.coverage)[] = ["national", "intl", "regional", "wire"];
  const parts = order.map((k) => [k, counts[k] ?? 0] as const).filter(([, n]) => n > 0);
  const total = parts.reduce((s, [, n]) => s + n, 0);
  if (total === 0) return null;
  const gap = 3;
  const usable = width - gap * (parts.length - 1);
  let x = 0;
  return (
    <svg width={width} height={height}>
      {parts.map(([k, n]) => {
        const w = Math.max(6, Math.round((n / total) * usable));
        const el = <rect key={k} x={x} y={0} width={w} height={height} rx={height / 2} fill={c.coverage[k]} />;
        x += w + gap;
        return el;
      })}
    </svg>
  );
}

const fit = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1).trimEnd()}…` : s);

/**
 * The share card, 1200 × 630, the record's header at poster scale (DESIGN.md
 * § Share cards): masthead · a mono meta line · the headline in the record
 * voice · the summary in the reading voice · a rule · the coverage bar with
 * its count on the left and the headline's provenance on the right. No
 * photograph (never a publisher's), no colour but the bar and the mark.
 */
export function OgCard({ meta, headline, summary, coverage, coverageText, foot, host, kicker }: {
  meta: string[];
  headline: string;
  summary?: string | null;
  coverage?: { national?: number; intl?: number; regional?: number; wire?: number };
  coverageText?: string;
  foot: string;
  host: string;
  kicker?: string;
}) {
  const title = fit(headline, 130);
  const size = title.length > 100 ? 46 : title.length > 70 ? 52 : 60;
  const lede = summary ? fit(summary, 170) : null;
  return (
    <div style={{ width: W, height: H, display: "flex", flexDirection: "column", background: c.ground, color: c.ink, padding: `${PAD - 8}px ${PAD}px ${PAD - 12}px` }}>
      <Masthead host={host} kicker={kicker} />
      <div style={{ display: "flex", flexDirection: "column", flex: 1, justifyContent: "center", paddingTop: 20, paddingBottom: 20 }}>
        {meta.length > 0 && (
          <div style={{ display: "flex", gap: 14, fontFamily: OG_MONO, fontSize: 17, color: c.inkFaint, letterSpacing: 1, textTransform: "uppercase" }}>
            {meta.map((m, i) => (
              <span key={i} style={{ display: "flex", gap: 14 }}>{i > 0 && <span style={{ color: c.lineStrong }}>·</span>}<span>{m}</span></span>
            ))}
          </div>
        )}
        <div style={{ marginTop: 14, fontFamily: displayStack(title), fontSize: size, fontWeight: 700, lineHeight: 1.12, letterSpacing: -1, maxWidth: 1040, display: "flex" }}>{title}</div>
        {lede && <div style={{ marginTop: 16, fontFamily: bodyStack(lede), fontSize: 26, lineHeight: 1.45, color: c.inkMuted, maxWidth: 980, display: "flex" }}>{lede}</div>}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: `1px solid ${c.line}`, paddingTop: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          {coverage && <CoverageBarSvg counts={coverage} />}
          {coverageText && <span style={{ fontFamily: OG_MONO, fontSize: 16, color: c.inkFaint }}>{coverageText}</span>}
        </div>
        <span style={{ fontFamily: OG_MONO, fontSize: 16, color: c.inkFaint }}>{foot}</span>
      </div>
    </div>
  );
}

/**
 * The quote card (PLAN-LAUNCH §6): a verbatim quote in the record's italic,
 * who said it and their role in the reading voice, and the outlet it was
 * printed in — the honesty line: VERBATIM IN <LANGUAGE> · outlet · date. The
 * most shared thing on WhatsApp is a sentence someone said.
 *
 * The language belongs on that line and used to be missing from it. Verbatim is
 * checked against the ARTICLE (enrichment/claims.py), so an outlet's own
 * translation passes — and this card is the one place the word VERBATIM is
 * asserted in isolation, with no outlet list and no other quote beside it to
 * hint that a language was involved. "Verbatim in Kannada · TV9 Kannada" is
 * true of a Kannada rendering of words spoken in English; "Verbatim" alone is
 * not. Falls back to the old line when the row carries no language.
 */
export function QuoteCard({ quote, speaker, role, outlet, when, host, storyTitle, lang, translated }: { quote: string; speaker: string; role?: string | null; outlet: string; when?: string | null; host: string; storyTitle?: string | null; lang?: string | null; translated?: boolean }) {
  const q = fit(quote, 230);
  const size = q.length > 170 ? 38 : q.length > 110 ? 44 : 52;
  return (
    <div style={{ width: W, height: H, display: "flex", flexDirection: "column", background: c.ground, color: c.ink, padding: `${PAD - 8}px ${PAD}px ${PAD - 12}px` }}>
      <Masthead host={host} kicker="Who said what" />
      <div style={{ display: "flex", flexDirection: "column", flex: 1, justifyContent: "center", paddingTop: 16, paddingBottom: 16 }}>
        <div style={{ fontFamily: displayStack(q), fontStyle: "italic", fontSize: size, lineHeight: 1.3, letterSpacing: -0.5, maxWidth: 1040, display: "flex" }}>“{q}”</div>
        <div style={{ marginTop: 22, display: "flex", alignItems: "baseline", gap: 12 }}>
          <span style={{ fontFamily: bodyStack(speaker), fontSize: 26, fontWeight: 600 }}>{speaker}</span>
          {role && <span style={{ fontFamily: bodyStack(role), fontSize: 22, color: c.inkMuted }}>{fit(role, 60)}</span>}
        </div>
        {storyTitle && <div style={{ marginTop: 8, fontFamily: bodyStack(storyTitle), fontSize: 20, color: c.inkFaint, maxWidth: 980, display: "flex" }}>{fit(storyTitle, 110)}</div>}
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderTop: `1px solid ${c.line}`, paddingTop: 20, fontFamily: OG_MONO, fontSize: 16, color: c.inkFaint, letterSpacing: 1, textTransform: "uppercase" }}>
        <span>{honestyLine({ lang, outlet, when, translated })}</span>
        <span>{host}</span>
      </div>
    </div>
  );
}

/**
 * The foot of the quote card. VERBATIM only when nothing says otherwise, and
 * never over a quote shown to be the outlet's own translation: this card is
 * shared alone, and the word would be the one claim on it that is false.
 */
export function honestyLine({ lang, outlet, when, translated }: { lang?: string | null; outlet: string; when?: string | null; translated?: boolean }): string {
  const tail = when ? ` · ${when}` : "";
  if (translated && lang) return `Translated into ${langName(lang)} by ${outlet}${tail}`;
  return `Verbatim${lang ? ` in ${langName(lang)}` : ""} · ${outlet}${tail}`;
}

/** The site card: the promise, and the bar that is how a reader learns what Prism is. */
export function SiteCard({ headline, line, host }: { headline: string; line: string; host: string }) {
  return (
    <div style={{ width: W, height: H, display: "flex", flexDirection: "column", background: c.ground, color: c.ink, padding: `${PAD - 8}px ${PAD}px ${PAD - 12}px` }}>
      <Masthead host={host} />
      <div style={{ display: "flex", flexDirection: "column", flex: 1, justifyContent: "center" }}>
        <div style={{ fontFamily: OG_DISPLAY, fontSize: 72, fontWeight: 700, lineHeight: 1.05, letterSpacing: -2, maxWidth: 1000, display: "flex" }}>{headline}</div>
        <div style={{ marginTop: 22, fontFamily: OG_SANS, fontSize: 28, lineHeight: 1.45, color: c.inkMuted, maxWidth: 900, display: "flex" }}>{line}</div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 14, borderTop: `1px solid ${c.line}`, paddingTop: 20 }}>
        <CoverageBarSvg counts={{ national: 5, intl: 2, regional: 3 }} width={300} />
        <span style={{ fontFamily: OG_MONO, fontSize: 16, color: c.inkFaint }}>English national · International · Indian-language</span>
      </div>
    </div>
  );
}
