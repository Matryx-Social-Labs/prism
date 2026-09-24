import type { MonitoredFeed, SourceRef } from "@/lib/api";

/** Pure helpers on the reports, callable from server components (see lib/coverage.ts for why). */
export function fallbackCode(name: string | null | undefined): string {
  const words = (name ?? "").replace("—", " ").split(/\s+/).filter((w) => w && !/^(the|of|news|&|and)$/i.test(w));
  if (words.length === 0) return "?";
  return (words.length === 1 ? words[0].slice(0, 2) : words.slice(0, 3).map((w) => w[0]).join("")).toUpperCase();
}

/** One index for [n], shared by the quotes and the report cards. */
export function indexSources(sources: SourceRef[]): Map<string, number> {
  return new Map(sources.map((s, i) => [s.article_id, i + 1]));
}

// The most-read Indian languages, largest first: a language here with no
// outlet yet is a gap in the record, and the page says so.
export const INDIAN_LANGUAGES = ["hi", "bn", "mr", "te", "ta", "gu", "ur", "kn", "or", "ml", "pa", "as"];

export function byLanguage(feeds: MonitoredFeed[]): [string, MonitoredFeed[]][] {
  const groups = new Map<string, MonitoredFeed[]>();
  for (const f of feeds) groups.set(f.language ?? "en", [...(groups.get(f.language ?? "en") ?? []), f]);
  const order = (code: string) => (code === "en" ? -1 : INDIAN_LANGUAGES.indexOf(code) === -1 ? 99 : INDIAN_LANGUAGES.indexOf(code));
  return [...groups.entries()].sort(([a], [b]) => order(a) - order(b));
}

export function missingLanguages(feeds: MonitoredFeed[]): string[] {
  const read = new Set(feeds.map((f) => f.language));
  return INDIAN_LANGUAGES.filter((code) => !read.has(code));
}
