// Founder share links, the admin's half (/admin/marketing; common/share_links
// is the API's). What a pasted address is, what the page it opens says, a post
// for each platform written only from that page's own facts, and the button
// that opens the platform with it. Nothing here counts anything.

import { fetchArchiveDay, fetchEntity, fetchEvent, fetchSources, fetchStateHub, fetchTrendingStory } from "@/lib/api";
import { dayRevalidate, longDay, parseDay } from "@/lib/archive";
import { monitoredText } from "@/lib/coverage";
import { findQuote } from "@/lib/quotes";
import { stateBySlug } from "@/lib/regions";

export type Platform =
  | "x" | "instagram" | "linkedin" | "facebook" | "threads" | "youtube" | "reddit" | "whatsapp" | "telegram"
  | "email" | "newsletter" | "producthunt" | "hn" | "peerlist" | "launchpadindia" | "devto" | "press";

/** The platforms in the order a founder reaches for them, as they are written. */
export const PLATFORM_LABEL: Record<Platform, string> = {
  whatsapp: "WhatsApp", x: "X", instagram: "Instagram", linkedin: "LinkedIn", facebook: "Facebook", threads: "Threads",
  telegram: "Telegram", reddit: "Reddit", youtube: "YouTube", email: "Email", newsletter: "Newsletter",
  producthunt: "Product Hunt", hn: "Hacker News", peerlist: "Peerlist", launchpadindia: "LaunchPad India", devto: "DEV", press: "Press",
};

// The pages a link may open, as common/share_links.PAGES has them (the API
// decides; this is the preview's reading of the same list).
const KINDS: Record<string, string> = {
  "": "landing", about: "about", plus: "plus", feed: "feed", archive: "archive", story: "story", trending: "trending",
  entity: "entity", state: "state", sector: "sector", subject: "subject", sources: "sources", pulse: "pulse", press: "press",
  "for-publishers": "publishers",
};
const SITE_HOSTS = new Set(["readprism.news", "www.readprism.news"]);

/** The path a pasted address or path opens on this site, or null when it is not one of Prism's public pages. */
export function targetPath(input: string, here?: string): string | null {
  const v = input.trim();
  if (!v || v.startsWith("//")) return null;
  let path = v;
  if (!v.startsWith("/")) {
    try {
      const u = new URL(v.includes("://") ? v : `https://${v}`);
      if (!/^https?:$/.test(u.protocol) || !(SITE_HOSTS.has(u.hostname) || u.host === here)) return null;
      path = u.pathname;
    } catch {
      return null;
    }
  }
  path = path.split(/[?#]/)[0].replace(/\/+$/, "") || "/";
  const first = path === "/" ? "" : path.split("/")[1];
  return first in KINDS ? path : null;
}

/** What the admin calls the page: a story, a quote, a day, a state… */
export function kindOf(path: string): string {
  const parts = path.split("/").filter(Boolean);
  if (parts[0] === "story" && parts[2] === "quote" && parts[3]) return "quote";
  if (parts[0] === "feed" && parts[1]) return "day";
  return KINDS[parts[0] ?? ""] ?? "page";
}

/** What a page says about itself, for the label and the post: its own facts only. */
export type Facts =
  | { kind: "story"; title: string; outlets: number; monitored: number | null }
  | { kind: "quote"; speaker: string; story: string }
  | { kind: "trending"; title: string }
  | { kind: "entity"; name: string; records: number; quotes: number }
  | { kind: "state"; name: string; multi: number; days: number }
  | { kind: "day"; long: string; multi: number | null }
  | { kind: "page"; name: string; path: string };

const PAGE_NAME: Record<string, string> = {
  "/": "The front page (landing)", "/feed": "Today's record", "/plus": "Prism Plus", "/about": "About Prism",
  "/archive": "The archive", "/sources": "The outlets Prism reads", "/state": "Every state", "/press": "Press",
};

/** The facts of the page a path opens, read from the same public API the page is built from. */
export async function describe(path: string): Promise<Facts> {
  const [first, a, b, c] = path.split("/").filter(Boolean);
  if (first === "story" && a && b === "quote" && c) {
    const e = await fetchEvent(a);
    const q = findQuote(e.claims, c, e.quote_aliases);
    if (q) return { kind: "quote", speaker: q.speaker, story: e.title };
  }
  if (first === "story" && a) {
    const e = await fetchEvent(a);
    const outlets = new Set(e.sources.map((s) => s.publisher ?? s.source_name)).size;
    return { kind: "story", title: e.title, outlets, monitored: e.monitored_outlets ?? (await fetchSources())?.outlets ?? null };
  }
  if (first === "trending" && a) {
    const s = await fetchTrendingStory(a);
    if (s) return { kind: "trending", title: s.label };
  }
  if (first === "entity" && a) {
    const p = await fetchEntity(a);
    if (p) return { kind: "entity", name: p.entity.name, records: p.record_count, quotes: p.quote_count ?? 0 };
  }
  const hub = first === "state" && a ? stateBySlug(a) : null;
  if (hub) {
    const s = await fetchStateHub(hub.code);
    if (s) return { kind: "state", name: hub.name, multi: s.multi_outlet, days: s.window_days };
  }
  const day = first === "feed" && a ? parseDay(a) : null;
  if (day) {
    const d = await fetchArchiveDay(day, dayRevalidate(day));
    if (d) return { kind: "day", long: longDay(day), multi: d.read ? d.multi_outlet : null };
  }
  return { kind: "page", name: PAGE_NAME[path] ?? path, path };
}

/** The list's label for a page: its headline, name or date. */
export function label(f: Facts): string {
  switch (f.kind) {
    case "story": case "trending": return f.title;
    case "quote": return `${f.speaker}, in: ${f.story}`;
    case "entity": case "state": return f.name;
    case "day": return f.long;
    case "page": return f.name;
  }
}

const plural = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** The front page's own sentence (app/page.tsx), for a page with nothing to count. */
const PROMISE = "Follow the story, not the headlines. One page per Indian news story, from a public list of outlets in English and Indian languages: every report, who covered it, and who said what, word for word.";

/** What the post says, before the link: the page's facts in the product's voice, no number it does not print. */
export function body(f: Facts): string {
  switch (f.kind) {
    case "story":
      return `${f.title}\n\nReported by ${monitoredText(f.outlets, f.monitored)}${f.outlets === 1 ? " so far" : ""}: every report, and who said what, on one page.`;
    case "quote":
      return `What ${f.speaker} said, as the article printed it, with every outlet that reported the story.`;
    case "trending":
      return `${f.title}\n\nThe story so far, on one page, with who reported each part.`;
    case "entity":
      return `${f.name}: every Prism record that names them${f.quotes ? `, and ${plural(f.quotes, "quote", "quotes")} checked word for word against the article` : ""}.`;
    case "state":
      return `${f.name}: ${plural(f.multi, "story", "stories")} two or more monitored outlets reported in the last ${f.days} days, with who reported each.`;
    case "day":
      return f.multi === null ? `The record for ${f.long}.` : `The record for ${f.long}: ${plural(f.multi, "story", "stories")} reported by two or more monitored outlets, by subject.`;
    case "page":
      return f.path === "/plus" ? "Prism Plus: what it adds, and what it costs, GST included." : PROMISE;
  }
}

/** X counts every link as 23 characters, whatever its length. */
export const X_LIMIT = 280;
const X_LINK = 23;

/** A post's length as X counts it, the link included. */
export function xLength(text: string): number {
  return [...text].length + 1 + X_LINK;
}

/** The post for a platform: the link where the platform does not add it, cut to fit X. */
export function draft(f: Facts, platform: Platform, link: string): string {
  const text = body(f);
  if (platform === "x") {
    const room = X_LIMIT - 1 - X_LINK;
    return [...text].length <= room ? text : `${[...text].slice(0, room - 1).join("").trimEnd()}…`;
  }
  // No link in an Instagram caption: it is not clickable there (the bio, or a Story's link sticker).
  if (platform === "instagram") return text;
  return `${text}\n\n${link}`;
}

const enc = encodeURIComponent;

/** The address that opens the platform with the post in it, or null where there is none (copy it instead). */
export function shareUrl(platform: Platform, link: string, post: string, title: string): string | null {
  switch (platform) {
    case "x": return `https://x.com/intent/post?text=${enc(post)}&url=${enc(link)}`;
    case "whatsapp": return `https://wa.me/?text=${enc(post)}`;
    case "telegram": return `https://t.me/share/url?url=${enc(link)}&text=${enc(post.replace(`\n\n${link}`, ""))}`;
    case "linkedin": return `https://www.linkedin.com/sharing/share-offsite/?url=${enc(link)}`;
    case "facebook": return `https://www.facebook.com/sharer/sharer.php?u=${enc(link)}`;
    case "threads": return `https://www.threads.net/intent/post?text=${enc(post)}`;
    case "reddit": return `https://www.reddit.com/submit?url=${enc(link)}&title=${enc(title)}`;
    case "email": return `mailto:?subject=${enc(title)}&body=${enc(post)}`;
    default: return null;
  }
}

/** The pages with a share card of their own (lib/cards); every other page shares the brand card. */
const OWN_CARD = new Set(["story", "trending", "entity", "state", "feed"]);

/** Where a page's share images are: the link preview, and Instagram's post and Story shapes (/card). */
export function cardImages(path: string): { preview: string; portrait: string; story: string } {
  const [, first, second] = path.split("/");
  const own = OWN_CARD.has(first) && !!second;
  const tail = own ? path : "/site";
  return { preview: own ? `${path}/opengraph-image` : "/opengraph-image", portrait: `/card/portrait${tail}`, story: `/card/story${tail}` };
}
