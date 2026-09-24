import type { OutletRef } from "@/lib/api";
import { langName } from "@/lib/languages";

/**
 * The coverage arithmetic, with no React in it, so a SERVER component (the
 * landing, a page) can call it. Coverage.tsx is "use client" for its hover
 * and image-error handlers; a function imported from a client module into a
 * server component is a reference, not a function — calling it throws
 * "Attempted to call coverageText() from the server", which took the landing
 * and /about down for two days (2026-09-18 → 20). Helpers live here; the
 * client module re-exports them for its own callers.
 */
export const ORIGINS = ["national", "intl", "regional", "wire"] as const;
export type Origin = (typeof ORIGINS)[number];
export const ORIGIN_LABEL: Record<Origin, string> = {
  national: "English national",
  intl: "International",
  regional: "Indian-language",
  wire: "Wire / agency",
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
  return codes.map(langName).join(", ");
}

/** "9 outlets · 2 languages" — counts, never adjectives. */
export function coverageText(outlets: OutletRef[], fallbackCount?: number): string {
  const n = outlets.length ? publishers(outlets).length : (fallbackCount ?? 0);
  const langs = languagesOf(outlets);
  const parts = [`${n} ${n === 1 ? "outlet" : "outlets"}`];
  if (langs.length > 1) parts.push(`${langs.length} languages`);
  return parts.join(" · ");
}

/**
 * "2 of 27 monitored outlets": a story's count is out of the outlets Prism
 * reads, never out of everyone who covered it (the denominator made visible).
 * Without the set's size — an older payload — it stays the bare count, and a
 * total smaller than the count (a feed retired since) is not printed as a
 * fraction that reads as a mistake.
 */
export function monitoredText(count: number, monitored: number | null | undefined): string {
  if (!monitored || monitored < count) return `${count} ${count === 1 ? "outlet" : "outlets"}`;
  return `${count} of ${monitored} monitored outlets`;
}
