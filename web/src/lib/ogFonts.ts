// Fonts for the social cards.
//
// next/font can't help here: ImageResponse needs raw font bytes, not a CSS class.
// Without them Satori falls back to a built-in Latin face, so every Hindi, Tamil,
// Telugu, Bengali, Gujarati, Kannada or Malayalam headline rendered as a row of
// tofu boxes — on an India-first product whose most-shared surface is a WhatsApp
// preview.
//
// Each request asks Google for a SUBSET (`text=`), so we fetch only the glyphs
// this one headline actually uses — a few KB, not a megabyte — and the result is
// cached per (family, weight, text) for the life of the server process, which
// covers the repeat scrapes that follow a share.

// The Reservation Chart's grounds and inks (DESIGN.md), light mode: a share
// card is the chart's row at poster scale.
const DESIGN = {
  ground: "#f2f4ee",
  ink: "#141414",
  inkMuted: "#5c5f58",
  inkFaint: "#6d7068",
  line: "#d6dbcf",
} as const;

export const OG_COLORS = DESIGN;

// Script → the Noto family that covers it. Ordered by reach in the launch
// markets; the first hit wins, and a headline that mixes scripts is rare enough
// that one extra family is the right trade against fetching seven.
const SCRIPTS: [RegExp, string][] = [
  [/[ऀ-ॿ]/, "Noto Sans Devanagari"], // Hindi, Marathi
  [/[஀-௿]/, "Noto Sans Tamil"],
  [/[ఀ-౿]/, "Noto Sans Telugu"],
  [/[ঀ-৿]/, "Noto Sans Bengali"],
  [/[઀-૿]/, "Noto Sans Gujarati"],
  [/[ಀ-೿]/, "Noto Sans Kannada"],
  [/[ഀ-ൿ]/, "Noto Sans Malayalam"],
];

/** The Noto family needed for this text, or null when it is plain Latin. */
export function indicFamilyFor(text: string): string | null {
  return SCRIPTS.find(([re]) => re.test(text))?.[1] ?? null;
}

const cache = new Map<string, ArrayBuffer | null>();

async function fetchFont(family: string, weight: number, text: string): Promise<ArrayBuffer | null> {
  const key = `${family}:${weight}:${text}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;

  let data: ArrayBuffer | null = null;
  try {
    const url =
      `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family)}:wght@${weight}` +
      `&text=${encodeURIComponent(text)}`;
    // Without a modern UA Google serves a TTF fallback; Satori reads either, but
    // the woff2 is a fraction of the size.
    const css = await fetch(url, {
      headers: { "User-Agent": "Mozilla/5.0 Chrome/120 Safari/537.36" },
    }).then((r) => (r.ok ? r.text() : ""));
    const src = css.match(/src:\s*url\(([^)]+)\)/)?.[1];
    if (src) {
      const res = await fetch(src);
      if (res.ok) data = await res.arrayBuffer();
    }
  } catch {
    // A card in the wrong typeface beats no card: the caller renders without it.
  }
  cache.set(key, data);
  return data;
}

type OgFont = { name: string; data: ArrayBuffer; weight: 400 | 600; style: "normal" };

/**
 * Fonts for one card. Fraunces carries the headline, IBM Plex Mono the
 * provenance eyebrow — the two voices DESIGN.md assigns to those jobs. An Indic
 * family is added only when the text needs one.
 *
 * Pass EVERY string the card draws, including the tagline and any entity list.
 * The subset contains exactly the glyphs you ask for, so anything omitted here
 * silently disappears from the render — the first cut of this subsetted on the
 * headline alone and the tagline came out as "Every perspective." with the space
 * dropped, because the space wasn't in the requested set.
 *
 * Returns whatever loaded; an empty array is a valid outcome and just means the
 * card renders in Satori's default face rather than failing the share.
 */
export async function ogFonts(...text: string[]): Promise<OgFont[]> {
  // Dedupe to characters: the URL carries the glyph set, not the sentences.
  // Both cases: the card sets its labels in capitals with text-transform, and
  // a subset fetched for "filed" has no F to transform it into.
  const joined = text.join(" ");
  const all = [...new Set((joined + joined.toUpperCase()).split(""))].join("");
  const indic = indicFamilyFor(all);
  // The three voices: Teko for structure (the count, the wordmark), Hind for
  // the headline, Martian Mono for provenance.
  const wanted: [string, number, string][] = [
    ["Teko", 500, all],
    ["Hind", 500, all],
    ["Martian Mono", 400, all],
    ...(indic ? ([[indic, 500, all]] as [string, number, string][]) : []),
  ];

  const loaded = await Promise.all(
    wanted.map(async ([family, weight, text]) => {
      const data = await fetchFont(family, weight, text);
      return data ? { name: family, data, weight: weight >= 500 ? 500 : 400, style: "normal" } : null;
    }),
  );
  return loaded.filter((f): f is OgFont => f !== null);
}

/** font-family stack for the headline, Indic first so it wins for those glyphs. */
export function displayStack(headline: string): string {
  const indic = indicFamilyFor(headline);
  return [indic, "Hind", "sans-serif"].filter(Boolean).join(", ");
}

export const OG_MONO = "Martian Mono, monospace";
export const OG_DISPLAY = "Teko, sans-serif";
