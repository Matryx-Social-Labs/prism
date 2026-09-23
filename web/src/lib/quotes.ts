// A quote's address: `<speaker index>-<claim index>` in the order the record
// lists them, so /story/<id>/quote/<n> names one verbatim sentence for the
// quote card (lib/ogCard QuoteCard) and the share link on each quote.
import type { ClaimOut, SpeakerClaims } from "@/lib/api";

export const quoteId = (speakerIdx: number, claimIdx: number) => `${speakerIdx}-${claimIdx}`;

export function findQuote(groups: SpeakerClaims[] | null | undefined, id: string) {
  const m = /^(\d+)-(\d+)$/.exec(id);
  if (!m || !groups) return null;
  const sp = groups[Number(m[1])];
  const c = sp?.claims[Number(m[2])];
  return sp && c ? { speaker: sp.speaker, role: sp.role ?? null, claim: c } : null;
}


/**
 * A speaker's quotes in the order THIS reader should meet them, carrying each
 * quote's position in the server's array.
 *
 * The position matters as much as the order. `quoteId` addresses a quote by its
 * index, and the OG card resolves that index against the API's own ordering —
 * so a reader-specific display order that renumbered the quotes would hand a
 * Kannada reader a share link whose card shows a different sentence.
 *
 * The API already round-robins the languages so no language can be pushed out
 * of the fold, English first (PRODUCT.md: English-first display for a reader
 * who has expressed no preference). This lifts the reader's own languages to
 * the front of that rotation and leaves everything else alone — `sort` is
 * stable, so equal ranks keep the API's order.
 */
export function orderForReader(
  claims: ClaimOut[],
  prefer: readonly string[],
): { claim: ClaimOut; index: number }[] {
  const numbered = claims.map((claim, index) => ({ claim, index }));
  const buckets = new Map<string, typeof numbered>();
  for (const item of numbered) {
    const key = item.claim.lang ?? "";
    const bucket = buckets.get(key);
    if (bucket) bucket.push(item);
    else buckets.set(key, [item]);
  }
  if (buckets.size < 2 || prefer.length === 0) return numbered;
  const rank = (lang: string) => {
    const at = prefer.indexOf(lang);
    return at < 0 ? prefer.length : at;
  };
  const order = [...buckets.keys()].sort((a, b) => rank(a) - rank(b));
  const deepest = Math.max(...[...buckets.values()].map((b) => b.length));
  const out: typeof numbered = [];
  for (let i = 0; i < deepest; i += 1) {
    for (const lang of order) {
      const item = buckets.get(lang)![i];
      if (item) out.push(item);
    }
  }
  return out;
}
