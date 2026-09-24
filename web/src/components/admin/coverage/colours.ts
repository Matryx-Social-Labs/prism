// A colour per language in the coverage network, largest language first;
// past five, one colour for the rest, so no two languages share one.

import { SERIES } from "@/components/admin/charts/format";
import type { Coverage } from "@/lib/admin";
import { langName } from "@/lib/languages";

const OTHER = "Other languages";

export const langWord = (code: string) => (code === "unknown" ? "Not given" : langName(code));

export function languageColours(perLanguage: Coverage["per_language"]) {
  const own = perLanguage.slice(0, SERIES.length - 1).map((l) => l.language);
  const colour = (code: string) => SERIES[own.includes(code) ? own.indexOf(code) : SERIES.length - 1];
  const key = [
    ...own.map((code) => ({ label: langWord(code), color: colour(code) })),
    ...(perLanguage.length > own.length ? [{ label: OTHER, color: SERIES[SERIES.length - 1] }] : []),
  ];
  return { colour, key };
}

