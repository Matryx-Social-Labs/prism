import type { EntityOut } from "@/lib/api";

/**
 * Finds the story's named entities inside a run of text so the record can
 * mark them (DESIGN.md § Entity marks). Rules, all about reading comfort:
 *
 * - Longest name first, so "Indian Navy" wins over "India" inside it.
 * - Whole words only, Unicode-aware, case-sensitive for names shorter than
 *   four characters (so "US" never marks "us") and case-insensitive otherwise.
 * - ONE mark per entity per passage: the first mention. A paragraph in which
 *   every "India" is underlined is a paragraph nobody finishes. A passage
 *   rendered as several blocks (the read-along splits sentences) goes through
 *   markBlocks, which is pure — no set mutated during render, which React's
 *   strict-mode double render would otherwise turn into vanishing marks.
 * - Never inside another mark; never overlapping.
 *
 * Pure function over strings; the component decides how a mark looks.
 */
export type Segment = { text: string; entity?: EntityOut };

const escape = (s: string) => s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
const isWord = (ch: string | undefined) => ch != null && /[\p{L}\p{N}]/u.test(ch);

export function markEntities(text: string, entities: EntityOut[], seen?: Set<string>): Segment[] {
  if (!text || entities.length === 0) return [{ text }];
  const names = [...new Map(entities.map((e) => [e.name.trim(), e])).values()]
    .filter((e) => e.name.trim().length >= 2)
    .sort((a, b) => b.name.length - a.name.length);
  const taken: [number, number, EntityOut][] = [];
  for (const e of names) {
    const name = e.name.trim();
    if (seen?.has(name)) continue; // already marked earlier in this passage
    const re = new RegExp(escape(name), name.length < 4 ? "g" : "gi");
    let m: RegExpExecArray | null;
    while ((m = re.exec(text))) {
      const start = m.index;
      const end = start + m[0].length;
      if (isWord(text[start - 1]) || isWord(text[end])) continue; // inside a word
      if (taken.some(([s, t]) => start < t && end > s)) continue; // overlaps a longer name
      taken.push([start, end, e]);
      seen?.add(name);
      break; // first mention only
    }
  }
  if (taken.length === 0) return [{ text }];
  taken.sort((a, b) => a[0] - b[0]);
  const out: Segment[] = [];
  let cursor = 0;
  for (const [s, t, e] of taken) {
    if (s > cursor) out.push({ text: text.slice(cursor, s) });
    out.push({ text: text.slice(s, t), entity: e });
    cursor = t;
  }
  if (cursor < text.length) out.push({ text: text.slice(cursor) });
  return out;
}

/** Several blocks of one passage: each entity marked once across all of them, in reading order. */
export function markBlocks(texts: string[], entities: EntityOut[]): Segment[][] {
  const seen = new Set<string>();
  return texts.map((t) => markEntities(t, entities, seen));
}

/** A reader's word for the pipeline's type: "government|subject" → "Government". */
export function entityKind(e: EntityOut): string {
  const t = (e.entity_type || "").split("|")[0].replace(/_/g, " ");
  const KIND: Record<string, string> = {
    person: "Person", organization: "Organisation", government: "Government", company: "Company",
    location: "Place", place: "Place", event: "Event", product: "Product", party: "Political party",
  };
  return KIND[t] ?? (t ? t[0].toUpperCase() + t.slice(1) : "Named");
}
