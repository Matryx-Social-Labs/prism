// A quote's address: `<speaker index>-<claim index>` in the order the record
// lists them, so /story/<id>/quote/<n> names one verbatim sentence for the
// quote card (lib/ogCard QuoteCard) and the share link on each quote.
import type { SpeakerClaims } from "@/lib/api";

export const quoteId = (speakerIdx: number, claimIdx: number) => `${speakerIdx}-${claimIdx}`;

export function findQuote(groups: SpeakerClaims[] | null | undefined, id: string) {
  const m = /^(\d+)-(\d+)$/.exec(id);
  if (!m || !groups) return null;
  const sp = groups[Number(m[1])];
  const c = sp?.claims[Number(m[2])];
  return sp && c ? { speaker: sp.speaker, role: sp.role ?? null, claim: c } : null;
}
