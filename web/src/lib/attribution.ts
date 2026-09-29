// Launch attribution (marketing audit 06 §2.3). A link Prism hands out carries
// a campaign word — https://www.readprism.news/?ref=producthunt — and the first
// page of a visit counts it once, as one word of a closed list (a word not on
// it counts as "other"), then takes it out of the address bar so the link a
// reader copies, and the canonical, stay clean. Nothing about the reader.

/** Mirrors common/usage.CAMPAIGNS; the API drops any other word. */
export const CAMPAIGNS = [
  "producthunt", "hn", "peerlist", "launchpadindia", "reddit", "x", "linkedin", "whatsapp",
  "telegram", "newsletter", "digest", "devto", "press", "other",
] as const;

// How the same place is spelt in the wild (utm_source is written by whoever
// made the link), after lowercasing, dropping a www. and a TLD, and anything
// that is not a letter or a digit.
const ALIASES: Record<string, string> = {
  ph: "producthunt", hackernews: "hn", ycombinator: "hn", newsycombinator: "hn", twitter: "x", tco: "x",
  wa: "whatsapp", dev: "devto", lnkd: "linkedin", launchpad: "launchpadindia",
};

/** The campaign word a link carried: `?ref=`, else `utm_source`; null when neither. */
export function campaignWord(params: URLSearchParams): string | null {
  const raw = params.get("ref") || params.get("utm_source");
  if (!raw) return null;
  const key = raw.trim().toLowerCase().replace(/^www\./, "").replace(/\.(com|io|to|in|org|net|co)$/, "").replace(/[^a-z0-9]/g, "");
  const word = ALIASES[key] ?? key;
  return (CAMPAIGNS as readonly string[]).includes(word) ? word : "other";
}

/** The address without `ref` and `utm_*` (path, the rest of the query, hash), or null when it carried none. */
export function withoutCampaign(href: string): string | null {
  const url = new URL(href);
  const keys = [...url.searchParams.keys()].filter((k) => k === "ref" || k.startsWith("utm_"));
  if (!keys.length) return null;
  keys.forEach((k) => url.searchParams.delete(k));
  return url.pathname + url.search + url.hash;
}

/** The `?s=` marker a Share button puts on a link (lib/analytics.shareSurface; common/usage.SHARE_SURFACES). */
export function isShareMarker(s: string | null): boolean {
  return s === "story" || s === "quote" || s === "trending" || s === "other";
}
