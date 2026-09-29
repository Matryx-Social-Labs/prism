// A quote's address, /story/<id>/quote/<n>: the API's `id`, a hash of the
// quote's words, so a newer report can never renumber a link already shared
// (the quote card, lib/ogCard QuoteCard, and the share link on each quote).
// Before 27 Sep 2026 the address was `<speaker index>-<claim index>` in the
// order the record listed them; the API maps each such position to the quote
// now holding its words (`quote_aliases`), and an older payload without the
// map is still read by position.
import type { ClaimOut, SpeakerClaims } from "@/lib/api";
import { istTime, shortDate } from "@/lib/dateline";

export const quoteId = (speakerIdx: number, claimIdx: number) => `${speakerIdx}-${claimIdx}`;

/** Where a quote's Share link points: its words' id, or its position on an older payload. */
export const quoteAddress = (claim: ClaimOut, speakerIdx: number, claimIdx: number) => claim.id ?? quoteId(speakerIdx, claimIdx);

export function findQuote(
  groups: SpeakerClaims[] | null | undefined,
  id: string,
  aliases?: Record<string, string> | null,
): { speaker: string; role: string | null; claim: ClaimOut; id: string } | null {
  if (!groups) return null;
  const m = /^(\d+)-(\d+)$/.exec(id);
  if (m && aliases) {
    // A link shared before the quote checks: withdrawn words have no entry.
    const to = aliases[id];
    return to ? findQuote(groups, to) : null;
  }
  if (m) {
    const sp = groups[Number(m[1])];
    const c = sp?.claims[Number(m[2])];
    return sp && c ? { speaker: sp.speaker, role: sp.role ?? null, claim: c, id } : null;
  }
  for (const sp of groups) {
    // Another outlet's copy of the words resolves to the row that cites them.
    const c = sp.claims.find((x) => x.id === id || x.also_in?.some((a) => a.id === id));
    if (c) return { speaker: sp.speaker, role: sp.role ?? null, claim: c, id: c.id ?? id };
  }
  return null;
}

/** Words an Indian-language article reported ("X said that…") rather than quoted. */
export const isReported = (claim: ClaimOut) => claim.speech === "reported";

/**
 * The words as the record may print them in a line of text (a share title, an
 * Ask prompt): a quote inside its quotation marks, reported words never —
 * marks would claim they are the speaker's exact words.
 */
export function saidWords(claim: ClaimOut, max?: number): string {
  const t = max && claim.quote_text.length > max ? `${claim.quote_text.slice(0, max - 1)}…` : claim.quote_text;
  return isReported(claim) ? t : `“${t}”`;
}

/** "2 quotes · 1 reported": what a card or the section holds, each kind counted apart. */
export function saidCount(claims: ClaimOut[]): string {
  const reported = claims.filter(isReported).length;
  return saidTally(claims.length - reported, reported);
}

/** saidCount from counts the server made (the entity page counts more than it sends). */
export function saidTally(quotes: number, reported: number): string {
  return [quotes && `${quotes} ${quotes === 1 ? "quote" : "quotes"}`, reported && `${reported} reported`].filter(Boolean).join(" · ");
}

/** "THE HINDU · [2] · 24 SEPT 11:30 IST": where and when, in the provenance voice. `n` is the report's [n] on its record. */
export function quoteProvenance(claim: ClaimOut, n: number | null | undefined): string {
  const when = claim.published_at ? `${shortDate(claim.published_at)} ${istTime(claim.published_at)} IST` : null;
  return [claim.source_name.toUpperCase(), n != null ? `[${n}]` : null, when?.toUpperCase()].filter(Boolean).join(" · ");
}

/**
 * How many outlets printed these quotes: the one each cites and every other
 * that carried the same words. Counted by masthead when the caller knows it
 * (The Times of India and its Delhi desk are one outlet), as the header counts.
 */
export function quoteOutlets(claims: ClaimOut[], masthead: (articleId: string) => string | null | undefined = () => null): number {
  return new Set(claims.flatMap((c) => [c, ...(c.also_in ?? [])].map((x) => masthead(x.article_id) ?? x.source_name))).size;
}

/**
 * The quote a showcase leads with (the landing's "Exact words", How it works'
 * step 04), with its speaker's other quotes after it. A quote only — words an
 * article reported are shown on the record, never as the showcase of "exact
 * words". Prefer words two or more outlets printed, then a speaker the
 * articles name an office for. Never simply the record's first — that showed
 * Majithia's post on X as the SSP's on the landing (audit P0 #2).
 */
export function showcaseQuote(groups: SpeakerClaims[] | null | undefined): SpeakerClaims | null {
  // Earlier wins a tie, so the API's own order (most-quoted speaker first) breaks it.
  const beats = (a: number[], b: number[]) => {
    const i = a.findIndex((x, k) => x !== b[k]);
    return i >= 0 && a[i] > b[i];
  };
  let best: { sp: SpeakerClaims; claim: ClaimOut; rank: number[] } | null = null;
  for (const sp of groups ?? []) {
    for (const claim of sp.claims.filter((c) => !isReported(c))) {
      const outlets = quoteOutlets([claim]);
      const rank = [outlets > 1 ? 1 : 0, sp.role ? 1 : 0, outlets];
      if (!best || beats(rank, best.rank)) best = { sp, claim, rank };
    }
  }
  if (!best) return null;
  const { sp, claim } = best;
  return { ...sp, claims: [claim, ...sp.claims.filter((c) => c !== claim)] };
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

export interface QuoteUnit {
  /** The rendering the reader meets first, with its position in the API's array. */
  lead: { claim: ClaimOut; index: number };
  /** The same statement as other outlets printed it, in other languages. */
  also: { claim: ClaimOut; index: number }[];
}

/**
 * One unit per STATEMENT, not per quote: renderings that share an utterance
 * collapse under the first one this reader meets. A card whose verdicts are
 * off or absent has no utterances, so every quote is its own unit and the
 * card is exactly what it was.
 *
 * The fold counts units. Otherwise a statement printed in English and Kannada
 * spends both of the card's two places on one thing the speaker said.
 */
export function unitsForReader(claims: ClaimOut[], prefer: readonly string[]): QuoteUnit[] {
  const units: QuoteUnit[] = [];
  const byUtterance = new Map<string, QuoteUnit>();
  for (const item of orderForReader(claims, prefer)) {
    const u = item.claim.utterance;
    const existing = u ? byUtterance.get(u) : undefined;
    if (existing) {
      existing.also.push(item);
      continue;
    }
    const unit: QuoteUnit = { lead: item, also: [] };
    units.push(unit);
    if (u) byUtterance.set(u, unit);
  }
  return units;
}
