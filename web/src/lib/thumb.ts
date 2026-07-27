// Ask publisher CDNs for an image the size we actually paint.
//
// next.config.ts sets images.unoptimized:true — news CDNs hotlink-block Vercel's
// optimizer, which fetches server-side — so whatever URL the ingester stored is
// what the phone downloads. That URL is a full-width article image: a 64px feed
// thumbnail was pulling 167KB from The Hindu and 455KB from Blogger, per visible
// row, on the India-first mid-range-Android target.
//
// Most of these CDNs already encode the size in the URL, so we can just ask for
// a smaller one. No proxy, no infrastructure, no optimizer.
//
// EVERY rule below was verified by fetching both URLs and comparing bytes; the
// numbers in the comments are real. Anything unrecognised passes through
// untouched — a wrong guess is a broken image in the feed, so this only rewrites
// what it has actually seen work.

/** Widths the rules below are tuned for. Roughly 2x the CSS box, for retina. */
export const THUMB_W = 200; // 56–64px boxes: feed row, trending row
export const CARD_W = 440; // 340px card image

function hindu(u: URL, width: number): string | null {
  // /public/incoming/<x>/articleN.ece/alternates/<VARIANT>/<name>.jpg
  // Verified: LANDSCAPE_1200 167,535B · FREE_435 33,960B · SQUARE_80 3,134B.
  // FREE_200, SQUARE_160, LANDSCAPE_270 and THUMBNAIL_BIG all 422 — the variant
  // set is fixed, so this picks from what exists rather than computing a size.
  if (!u.pathname.includes("/alternates/")) return null;
  const variant = width <= 96 ? "SQUARE_80" : "FREE_435";
  return u.href.replace(/\/alternates\/[^/]+\//, `/alternates/${variant}/`);
}

function toi(u: URL, width: number): string | null {
  // /photo/msid-132606785,imgsize-167905.cms → /thumb/msid-...,width-200,...
  // Verified: original 144,311B · width-200 4,944B (29x).
  const msid = u.pathname.match(/msid-(\d+)/)?.[1];
  if (!msid) return null;
  return `https://static.toiimg.com/thumb/msid-${msid},width-${width},resizemode-4.cms`;
}

function blogger(u: URL, width: number): string | null {
  // .../s1600/name.jpg → .../s200/name.jpg
  // Verified: s1600 455,550B · s200 8,472B (54x — the worst offender by far).
  if (!/\/s\d+\//.test(u.pathname)) return null;
  return u.href.replace(/\/s\d+\//, `/s${width}/`);
}

function tosshub(u: URL, width: number): string | null {
  // ?size=W:H — 16:9 matches the shape these are cropped to.
  // Verified: original 136,230B · size=350:197 18,515B (7x).
  u.searchParams.set("size", `${width}:${Math.round((width * 9) / 16)}`);
  return u.href;
}

const RULES: [RegExp, (u: URL, width: number) => string | null][] = [
  [/(^|\.)thgim\.com$/, hindu], // The Hindu, BusinessLine
  [/(^|\.)toiimg\.com$/, toi], // Times of India
  [/(^|\.)googleusercontent\.com$/, blogger],
  [/(^|\.)tosshub\.com$/, tosshub], // India Today, Aaj Tak
];

/**
 * A URL for the same image at roughly `width` px, when the CDN supports it.
 *
 * Returns the input unchanged for anything we haven't verified — including
 * Hindustan Times and LiveMint, which bake one fixed size into the path
 * (`/1600x900/`) and 404 on every other size tried, so there is nothing to ask
 * for. Those still need a resizer we control.
 */
export function thumbUrl(src: string, width: number = THUMB_W): string {
  try {
    const u = new URL(src);
    for (const [host, rule] of RULES) {
      if (host.test(u.hostname)) return rule(u, width) ?? src;
    }
  } catch {
    // Relative or malformed src (our own /og fallbacks) — leave it alone.
  }
  return src;
}
