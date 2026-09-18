import type { OutletRef } from "@/lib/api";

/**
 * The prism's work on one story (DESIGN.md § Coverage): the reporting split by
 * outlet origin — English national · international · Indian-language · wire —
 * in that fixed slot order, so no two adjacent segments collide for a
 * colour-blind reader. The count printed beside the bar is the legend; the bar
 * is never colour alone.
 */
export const ORIGINS = ["national", "intl", "regional", "wire"] as const;
export type Origin = (typeof ORIGINS)[number];
export const ORIGIN_LABEL: Record<Origin, string> = {
  national: "English national",
  intl: "International",
  regional: "Indian-language",
  wire: "Wire / agency",
};

const LANGUAGE_NAME: Record<string, string> = {
  en: "English", hi: "Hindi", kn: "Kannada", ta: "Tamil", te: "Telugu", bn: "Bengali", gu: "Gujarati",
  mr: "Marathi", pa: "Punjabi", ur: "Urdu", ml: "Malayalam", or: "Odia", ar: "Arabic", ru: "Russian",
};

export function coverageCounts(outlets: OutletRef[]): Record<Origin, number> {
  const c: Record<Origin, number> = { national: 0, intl: 0, regional: 0, wire: 0 };
  for (const o of outlets) if (o.origin in c) c[o.origin as Origin] += 1;
  return c;
}

/** Distinct mastheads behind the story: The Hindu's six state feeds count once. */
export function publishers(outlets: OutletRef[]): OutletRef[] {
  const seen = new Set<string>();
  return outlets.filter((o) => (seen.has(o.publisher) ? false : (seen.add(o.publisher), true)));
}

export function languagesOf(outlets: OutletRef[]): string[] {
  const seen: string[] = [];
  for (const o of outlets) {
    const l = o.language ?? "en";
    if (!seen.includes(l)) seen.push(l);
  }
  return seen;
}

export function languageNames(codes: string[]): string {
  return codes.map((c) => LANGUAGE_NAME[c] ?? c.toUpperCase()).join(", ");
}

/** "9 outlets · 2 languages" — counts, never adjectives. */
export function coverageText(outlets: OutletRef[], fallbackCount?: number): string {
  const n = outlets.length ? publishers(outlets).length : (fallbackCount ?? 0);
  const langs = languagesOf(outlets);
  const parts = [`${n} ${n === 1 ? "outlet" : "outlets"}`];
  if (langs.length > 1) parts.push(`${langs.length} languages`);
  return parts.join(" · ");
}

export function CoverageBar({
  outlets,
  fallbackCount,
  size = "sm",
  width,
  draw = false,
  className = "",
}: {
  outlets: OutletRef[];
  /** Rows written before outlets were served: draw the count as one national segment. */
  fallbackCount?: number;
  size?: "sm" | "lg";
  width?: number;
  /** Animate the segments in on first paint (once per page, never on re-sort). */
  draw?: boolean;
  className?: string;
}) {
  const counts = outlets.length ? coverageCounts(outlets) : { national: fallbackCount ?? 0, intl: 0, regional: 0, wire: 0 };
  const total = Object.values(counts).reduce((a, b) => a + b, 0) || 1;
  const w = width ?? (size === "lg" ? 120 : 72);
  return (
    <span className={`covbar ${size === "lg" ? "lg" : ""} ${draw ? "draw" : ""} ${className}`} aria-hidden="true">
      {ORIGINS.filter((k) => counts[k] > 0).map((k) => (
        <i key={k} className={`cov-${k}`} style={{ width: Math.max(4, Math.round((w * counts[k]) / total)) }} />
      ))}
    </span>
  );
}

export function CoverageLegend({ outlets, withCounts = true }: { outlets: OutletRef[]; withCounts?: boolean }) {
  const counts = coverageCounts(outlets);
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-[12.5px]" style={{ color: "var(--ink-2)" }}>
      {ORIGINS.filter((k) => counts[k] > 0).map((k) => (
        <span key={k} className="inline-flex items-center gap-1.5">
          <i className={`cov-${k} inline-block h-2.5 w-2.5 rounded-[3px]`} />
          {ORIGIN_LABEL[k]}
          {withCounts && <span className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{counts[k]}</span>}
        </span>
      ))}
    </div>
  );
}

/** Outlet monograms, distinct mastheads, at most `limit` then "+N". */
export function MonogramStack({ outlets, limit = 3, size = 26 }: { outlets: OutletRef[]; limit?: number; size?: number }) {
  const list = publishers(outlets);
  if (!list.length) return null;
  const shown = list.slice(0, limit);
  const more = list.length - shown.length;
  return (
    <span className="monogram-stack" aria-label={list.map((o) => o.name).join(", ")} role="img">
      {shown.map((o) => (
        <Monogram key={o.publisher} code={o.code} name={o.name} size={size} />
      ))}
      {more > 0 && (
        <span className="monogram" style={{ width: size, height: size, fontFamily: "var(--font-mono)", fontWeight: 500 }} aria-hidden>
          +{more}
        </span>
      )}
    </span>
  );
}

export function Monogram({ code, name, size = 26 }: { code: string; name: string; size?: number }) {
  return (
    <span className={`monogram ${code.length >= 4 ? "n4" : ""}`} style={{ width: size, height: size }} title={name} aria-hidden>
      {code}
    </span>
  );
}
