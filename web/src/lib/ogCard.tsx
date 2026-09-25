import type { ReactNode } from "react";

import { Check } from "@/components/icons";
import { ORIGINS, type Origin } from "@/lib/coverage";
import { shortDate, istTime } from "@/lib/dateline";
import { MARK_BAND, MARK_BOX, MARK_TRIANGLE, SPECTRUM_STOPS } from "@/lib/mark";
import { OG_COLORS, OG_DISPLAY, OG_MONO, OG_SANS, bodyStack, displayStack, indicBodyFamilyFor } from "@/lib/ogFonts";

// Share cards v3 (Claude Design, outside/ShareCards.html): 1200 × 630, the
// record's voices, a 3px rule under the masthead, the coverage bar in its slot
// colours with its counts, the address the card opens. Never a photograph.

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
const INNER = 1056; // W less the 72px sides

/** The legend's slot names, as the card prints them (short: the bar sits beside them). */
const SLOT: Record<Origin, string> = { national: "national", intl: "international", regional: "Indian-language", wire: "wire" };

const fit = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1).trimEnd()}…` : s);
const monoStack = (text: string) => [OG_MONO.split(",")[0], indicBodyFamilyFor(text), "monospace"].filter(Boolean).join(", ");

export type Tally = { counts: Record<Origin, number>; outlets: number; languages: string[] };

/**
 * Coverage as the card counts it: distinct mastheads per slot (The Hindu's six
 * state feeds count once), so the legend adds up to the outlet count beside
 * it; languages by how many reports carry them, most first.
 */
export function tally(list: { publisher?: string | null; origin?: string | null; language?: string | null }[]): Tally {
  const counts: Record<Origin, number> = { national: 0, intl: 0, regional: 0, wire: 0 };
  const seen = new Set<string>();
  const langs = new Map<string, number>();
  for (const o of list) {
    const l = o.language ?? "en";
    langs.set(l, (langs.get(l) ?? 0) + 1);
    if (!o.publisher || seen.has(o.publisher)) continue;
    seen.add(o.publisher);
    if (o.origin && o.origin in counts) counts[o.origin as Origin] += 1;
  }
  return { counts, outlets: seen.size, languages: [...langs].sort((a, b) => b[1] - a[1]).map(([l]) => l) };
}

/** 25 SEPT 14:02 IST — a card is cached for days, so a time always carries its day. */
export const stamp = (iso: string) => `${shortDate(iso)} ${istTime(iso)} IST`;

/**
 * The quote card's check line. "Word for word" is true of the ARTICLE — the
 * check (enrichment/claims.py) asks whether these words are in it — so it
 * holds for every quote the record prints; over an outlet's own translation
 * the card says so instead, and never "word for word" on its own.
 */
export const quoteCheckLine = (translated: boolean) =>
  translated ? "Checked against the article · the outlet translated these words" : "Word for word, checked against the article";

export type PillSpec = { label: string; dashed?: boolean; check?: boolean };

function Pill({ label, dashed, check, small }: PillSpec & { small?: boolean }) {
  const color = dashed ? c.inkMuted : c.ink;
  return (
    <div
      style={{
        display: "flex", alignItems: "center", gap: 8, flexShrink: 0, fontFamily: OG_SANS, fontSize: small ? 17 : 20, fontWeight: 600,
        lineHeight: 1, letterSpacing: 0, color, border: `2px ${dashed ? "dashed" : "solid"} ${color}`, borderRadius: 2, padding: small ? "6px 10px" : "9px 14px",
      }}
    >
      {check && <Check size={22} />}
      <span>{label}</span>
    </div>
  );
}

/** The frame every card shares: the ground, the mark and "Prism", the address, the 3px rule. */
function Frame({ address, ink, children }: { address: string; ink?: boolean; children: ReactNode }) {
  const fg = ink ? c.onInk : c.ink;
  return (
    <div style={{ width: W, height: H, display: "flex", flexDirection: "column", background: ink ? c.inkGround : c.ground, color: fg, padding: "56px 72px 60px" }}>
      <div style={{ display: "flex", alignItems: "center", gap: 14, paddingBottom: 22, borderBottom: `3px solid ${fg}` }}>
        <PrismMarkSvg size={44} ink={fg} />
        <span style={{ fontFamily: OG_DISPLAY, fontSize: 34, fontWeight: 600, letterSpacing: -0.34, lineHeight: 1 }}>Prism</span>
        <span style={{ marginLeft: "auto", fontFamily: OG_MONO, fontSize: 20, letterSpacing: 0.4, opacity: 0.72 }}>{fit(address, 72)}</span>
      </div>
      {children}
    </div>
  );
}

function MetaLine({ pill, parts, top = 36 }: { pill?: PillSpec | null; parts: string[]; top?: number }) {
  const text = parts.filter(Boolean).join(" · ").toUpperCase();
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: top, fontFamily: monoStack(text), fontSize: 21, letterSpacing: 0.63, color: c.inkMuted }}>
      {pill && <Pill {...pill} />}
      {text && <span>{text}</span>}
    </div>
  );
}

/** The coverage bar at poster scale, its legend of counts, and the count line on the right. */
function CoverageBlock({ counts, count, single }: { counts: Record<Origin, number>; count: string; single?: boolean }) {
  const parts = ORIGINS.map((k) => [k, counts[k]] as const).filter(([, n]) => n > 0);
  const bar = (
    <div style={{ display: "flex", gap: 6, height: 22, width: single ? 220 : INNER }}>
      {parts.map(([k, n]) => <div key={k} style={{ flexGrow: n, flexBasis: 0, height: 22, borderRadius: 2, background: c.coverage[k] }} />)}
    </div>
  );
  return (
    <div style={{ display: "flex", flexDirection: "column", marginTop: "auto" }}>
      {/* One source so far: a dashed edge round the bar (the design's outline, offset 4). */}
      {single ? <div style={{ display: "flex", alignSelf: "flex-start", margin: "0 0 0 -6px", padding: 4, border: `2px dashed ${c.inkFaint}` }}>{bar}</div> : bar}
      <div style={{ display: "flex", alignItems: "center", gap: 26, marginTop: 14, fontFamily: OG_SANS, fontSize: 21, color: c.inkMuted }}>
        {parts.map(([k, n]) => (
          <div key={k} style={{ display: "flex", alignItems: "center" }}>
            <div style={{ width: 14, height: 14, borderRadius: 2, background: c.coverage[k], marginRight: 8 }} />
            <span style={{ fontFamily: OG_MONO, fontSize: 22, fontWeight: 600, color: c.ink, marginRight: 6 }}>{n}</span>
            <span>{SLOT[k]}</span>
          </div>
        ))}
        <span style={{ marginLeft: "auto", fontFamily: OG_MONO, fontSize: 24, fontWeight: 600, color: c.ink }}>{count}</span>
      </div>
    </div>
  );
}

/**
 * A verified arc's route: one station per development, in order, the latest
 * filled. Labelled with the day only — a development's title is prose and has
 * no place in the provenance voice — every station when they fit, else the ends.
 */
function RouteLine({ dates }: { dates: string[] }) {
  const n = dates.length;
  const step = (INNER - 24) / (n - 1);
  const r = n > 12 ? 7 : 11;
  const day = (i: number) => shortDate(dates[i]).toUpperCase();
  // A day is printed once: stations that share it read as one run of dots.
  const labelled: number[] = [];
  for (const i of n <= 6 ? dates.map((_, k) => k) : [0, n - 1]) if (!labelled.length || day(i) !== day(labelled[labelled.length - 1])) labelled.push(i);
  return (
    <div style={{ display: "flex", flexDirection: "column", marginTop: 22 }}>
      <svg width={INNER} height={44} viewBox={`0 0 ${INNER} 44`}>
        <line x1={12} y1={22} x2={INNER - 12} y2={22} stroke={c.ink} strokeWidth={5} />
        {dates.map((_, i) =>
          i === n - 1 ? (
            <circle key={i} cx={12 + i * step} cy={22} r={r + 1} fill={c.ink} />
          ) : (
            <circle key={i} cx={12 + i * step} cy={22} r={r} fill={c.ground} stroke={c.ink} strokeWidth={4} />
          ),
        )}
      </svg>
      <div style={{ display: "flex", position: "relative", height: 22, marginTop: 6, fontFamily: OG_MONO, fontSize: 17, color: c.inkMuted }}>
        {labelled.map((i) => (
          <span key={i} style={i === n - 1 ? { position: "absolute", right: 0 } : { position: "absolute", left: i * step }}>
            {day(i)}
          </span>
        ))}
      </div>
    </div>
  );
}

/**
 * A record or a trending group: the status pill and the mono meta line, the
 * headline in the record voice, a verified arc's route, the counted bar.
 */
export function StoryCard({ address, pill, meta, headline, tally: t, count, single, route }: {
  address: string;
  pill?: PillSpec | null;
  meta: string[];
  headline: string;
  tally: Tally;
  count: string;
  single?: boolean;
  route?: string[] | null;
}) {
  const hasRoute = !!route && route.length > 1;
  const title = fit(headline, hasRoute ? 90 : 120);
  const size = hasRoute ? (title.length > 60 ? 52 : 62) : title.length > 95 ? 54 : title.length > 75 ? 60 : 66;
  return (
    <Frame address={address}>
      <MetaLine pill={pill} parts={meta} />
      <div style={{ display: "flex", marginTop: hasRoute ? 20 : 22, fontFamily: displayStack(title), fontSize: size, fontWeight: 600, lineHeight: 1.06, letterSpacing: -0.022 * size }}>
        {title}
      </div>
      {hasRoute && <RouteLine dates={route!} />}
      <CoverageBlock counts={t.counts} count={count} single={single} />
    </Frame>
  );
}

/**
 * The quote card: the words as the article printed them under a 6px ink rule,
 * who said it, where and when it was printed, and what the check proved.
 */
export function QuoteCard({ address, quote, speaker, role, meta, translated, storyTitle }: {
  address: string;
  quote: string;
  speaker: string;
  role?: string | null;
  meta: string[];
  translated: boolean;
  storyTitle?: string | null;
}) {
  const q = fit(quote, 240);
  const size = q.length > 180 ? 40 : q.length > 120 ? 46 : indicBodyFamilyFor(q) ? 50 : 54;
  const provenance = meta.filter(Boolean).join(" · ").toUpperCase();
  return (
    <Frame address={address}>
      <div style={{ display: "flex", flexDirection: "column", marginTop: "auto", borderLeft: `6px solid ${c.ink}`, paddingLeft: 34 }}>
        <div style={{ display: "flex", fontFamily: displayStack(q), fontStyle: "italic", fontSize: size, lineHeight: 1.26 }}>“{q}”</div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginTop: 24, fontFamily: bodyStack(speaker + (role ?? "")) }}>
          <span style={{ fontSize: 27, fontWeight: 600, lineHeight: 1.3 }}>{fit(speaker, 48)}</span>
          {role && <span style={{ fontSize: 22, color: c.inkMuted }}>{fit(role, 56)}</span>}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 14, marginTop: 8, fontFamily: monoStack(provenance), fontSize: 21, letterSpacing: 0.63, color: c.inkMuted }}>
          <span>{provenance}</span>
          {translated && <Pill label="translation" dashed small />}
        </div>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 20, marginTop: 30 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0, fontFamily: OG_SANS, fontSize: 21, fontWeight: 600, color: c.ink }}>
          <Check size={22} />
          <span>{quoteCheckLine(translated)}</span>
        </div>
        {storyTitle && !translated && (
          <span style={{ marginLeft: "auto", fontFamily: bodyStack(storyTitle), fontSize: 20, color: c.inkMuted, overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
            {storyTitle}
          </span>
        )}
      </div>
    </Frame>
  );
}

/** The site card's words: the promise, and what the product is, in one sentence. */
export const SITE_HEADLINE = "Follow the story, not the headlines.";
export const SITE_LINE = "One record per story, from monitored outlets across India's languages — every development, verified quote and source open to inspection.";

/** Every word a card draws that its route does not pass in, for the font subset (ogFonts). */
export const CARD_TEXT = [
  "Prism", ...Object.values(SLOT), "Verified record", "Verified", "Provisional grouping", "Grouping under review",
  "One source so far", "translation", quoteCheckLine(true), quoteCheckLine(false), "…",
].join(" ");

/** The site card, on the ink ground: the promise, one sentence, the slot colours. */
export function SiteCard({ headline, line, host }: { headline: string; line: string; host: string }) {
  const slots: [Origin, number, number][] = [["national", 5, 1], ["intl", 1.2, 1], ["regional", 4, 1], ["wire", 0.6, 0.6]];
  return (
    <Frame address={host} ink>
      <div style={{ display: "flex", marginTop: "auto", maxWidth: 760, fontFamily: OG_DISPLAY, fontSize: 92, fontWeight: 600, lineHeight: 1.06, letterSpacing: -2 }}>{headline}</div>
      <div style={{ display: "flex", marginTop: 22, maxWidth: 860, fontFamily: OG_SANS, fontSize: 28, lineHeight: 1.4, color: c.onInkMuted }}>{line}</div>
      <div style={{ display: "flex", gap: 6, height: 22, marginTop: 34 }}>
        {slots.map(([k, grow, opacity]) => <div key={k} style={{ flexGrow: grow, flexBasis: 0, borderRadius: 2, background: c.coverageOnInk[k], opacity }} />)}
      </div>
    </Frame>
  );
}
