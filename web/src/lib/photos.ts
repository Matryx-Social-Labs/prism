// The pictures a record or a story shows, chosen once: distinct (same URL, or
// the same picture under another URL — a perceptual hash within a few bits),
// one per publisher first (BBC's language editions upload one photo per
// edition), capped. Plain data, so a server page can build frames too.
import type { SourceRef, StoryPhoto } from "@/lib/api";
import { NEAR_DUPLICATE_BITS, hamming } from "@/lib/images";

const MAX = 8;

/** One frame of the photo deck, whichever page it comes from. */
export interface DeckPhoto {
  key: string;
  image_url: string;
  url: string; // the report it opens
  source_name: string;
  domain?: string | null;
  code?: string | null;
  title?: string | null;
  published_at?: string | null;
}

export function uniquePhotos(sources: SourceRef[], limit = MAX): SourceRef[] {
  const seen = new Set<string>();
  const hashes: string[] = [];
  const all = sources.filter((s) => {
    if (!s.image_url || !s.url || seen.has(s.image_url)) return false;
    seen.add(s.image_url);
    if (s.image_phash) {
      if (hashes.some((h) => hamming(h, s.image_phash!) <= NEAR_DUPLICATE_BITS)) return false;
      hashes.push(s.image_phash);
    }
    return true;
  });
  // One per publisher first: BBC's language editions upload the same picture
  // under new ids, and three in a row read as a repeat before another outlet.
  const firstOf = new Set<string>();
  const lead = all.filter((s) => { const k = s.publisher ?? s.source_name; return firstOf.has(k) ? false : (firstOf.add(k), true); });
  return [...lead, ...all.filter((s) => !lead.includes(s))].slice(0, limit);
}

export function framesFromSources(sources: SourceRef[]): DeckPhoto[] {
  return uniquePhotos(sources).map((s) => ({ key: s.article_id, image_url: s.image_url!, url: s.url!, source_name: s.source_name, domain: s.domain, code: s.code, title: s.title, published_at: s.published_at }));
}

export function framesFromStory(photos: StoryPhoto[]): DeckPhoto[] {
  return photos.filter((p) => p.article_url).map((p, i) => ({ key: `${i}-${p.url}`, image_url: p.url, url: p.article_url!, source_name: p.outlet?.name ?? "a report", domain: p.outlet?.domain, code: p.outlet?.code ?? null }));
}

