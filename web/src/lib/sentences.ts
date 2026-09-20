// The brief, one sentence per point. Intl.Segmenter (and the regex fallback)
// break after "N." in "N. Chandrasekaran" and after "Rs." — an initial or an
// abbreviation is not the end of a sentence, and a point that ends "…of N."
// with the next beginning "Chandrasekaran as…" read as a bug on the record
// (founder, 2026-09-21). Segments that end on one are glued to the next.
const NOT_AN_END = /(?:^|[\s(“"'])(?:[A-Z]|Mr|Mrs|Ms|Dr|Prof|Sr|Jr|St|No|Nos|Rs|Re|vs|Lt|Col|Gen|Maj|Capt|Sgt|Hon|Rev|Fr|Smt|Shri|Md|Adv|Justice|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec|Inc|Ltd|Pvt|Co|Corp|Govt|Dept|Univ|approx|est)\.$/;

export function sentences(text: string): string[] {
  let raw: string[];
  try {
    const seg = new Intl.Segmenter("en", { granularity: "sentence" });
    raw = [...seg.segment(text)].map((s) => s.segment.trim()).filter(Boolean);
  } catch {
    raw = (text.match(/[^.!?]+[.!?]+["’”]?|[^.!?]+$/g) ?? [text]).map((s) => s.trim()).filter(Boolean);
  }
  const out: string[] = [];
  for (const s of raw) {
    const prev = out[out.length - 1];
    if (prev !== undefined && NOT_AN_END.test(prev)) out[out.length - 1] = `${prev} ${s}`;
    else out.push(s);
  }
  return out;
}
