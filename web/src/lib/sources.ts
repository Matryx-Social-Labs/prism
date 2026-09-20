import type { SourceRef } from "@/lib/api";

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
