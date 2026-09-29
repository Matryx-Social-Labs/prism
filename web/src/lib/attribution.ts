// Launch attribution (marketing audit 06 §2.3). A link Prism hands out carries
// a campaign word — https://www.readprism.news/?ref=producthunt — and the first
// page of a visit counts it once, as one word of a closed list (a word not on
// it counts as "other"), then takes it out of the address bar so the link a
// reader copies, and the canonical, stay clean. Nothing about the reader.

import { send } from "@/lib/analytics";

/** Mirrors common/usage.CAMPAIGNS; the API drops any other word. */
export const CAMPAIGNS = [
  "producthunt", "hn", "peerlist", "launchpadindia", "reddit", "x", "linkedin", "whatsapp",
  "telegram", "newsletter", "digest", "devto", "press", "instagram", "facebook", "youtube",
  "threads", "email", "other",
] as const;

// How the same place is spelt in the wild (utm_source is written by whoever
// made the link), after lowercasing, dropping a www. and a TLD, and anything
// that is not a letter or a digit.
const ALIASES: Record<string, string> = {
  ph: "producthunt", hackernews: "hn", ycombinator: "hn", newsycombinator: "hn", twitter: "x", tco: "x",
  wa: "whatsapp", dev: "devto", lnkd: "linkedin", launchpad: "launchpadindia", ig: "instagram", fb: "facebook",
  mfacebook: "facebook", lfacebook: "facebook", youtu: "youtube", mail: "email",
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

// Founder links (/admin/marketing, common/share_links): a link made there
// carries its code in utm_content. The visit counts once against the code, and
// this tab remembers it (sessionStorage: gone when the tab closes) so that what
// the visit does next — a second story, a sign-in, the Plus page, the weekly
// email — counts once each against the same code. Never who; the API drops a
// code that is not a link.
const LINK_CODE = /^[2-9a-hjkmnp-z]{6}$/; // common/share_links.CODE
const LINK = "prism.link";
const LINK_GOALS = "prism.link.goals";

export type LinkGoal = "read2" | "signin" | "plus" | "digest";

/** The founder link's code a link carried (utm_content), or null. */
export function linkCode(params: URLSearchParams): string | null {
  const code = (params.get("utm_content") ?? "").trim().toLowerCase();
  return LINK_CODE.test(code) ? code : null;
}

/** Remember, for this tab only, the founder link this visit came by. */
export function rememberLink(code: string): void {
  try {
    window.sessionStorage.setItem(LINK, code);
  } catch {
    /* storage blocked: the arrival still counts, what follows does not */
  }
}

/** The founder link this tab's visit came by, or null. */
export function arrivedByLink(): string | null {
  try {
    const code = window.sessionStorage.getItem(LINK);
    return code && LINK_CODE.test(code) ? code : null;
  } catch {
    return null;
  }
}

/** Count a step once per tab against the founder link the visit came by; nothing when it came by none. */
export function linkGoal(goal: LinkGoal): void {
  const code = arrivedByLink();
  if (!code) return;
  try {
    const sent = (window.sessionStorage.getItem(LINK_GOALS) ?? "").split(",");
    if (sent.includes(goal)) return;
    window.sessionStorage.setItem(LINK_GOALS, [...sent.filter(Boolean), goal].join(","));
  } catch {
    return;
  }
  send("goal", `${code}:${goal}`);
}
