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

// The paper of record's grounds and inks (DESIGN.md § Colour, light): a share
// card is the record's header at poster scale.
// Design System v2 light tokens (design/tokens.json): share cards are light only.
const DESIGN = {
  ground: "#F7F6F2",
  surface: "#FFFFFF",
  ink: "#111317",
  inkMuted: "#3F434A",
  inkFaint: "#5B6069",
  line: "#DFDDD6",
  lineStrong: "#8E8B82",
  accent: "#0B57D0",
  coverage: { national: "#1E3A6E", intl: "#1583A8", regional: "#C4470F", wire: "#767872" },
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

async function fetchFont(family: string, weight: number, text: string, italic = false): Promise<ArrayBuffer | null> {
  const key = `${family}:${weight}:${italic ? "i" : "n"}:${text}`;
  const hit = cache.get(key);
  if (hit !== undefined) return hit;

  let data: ArrayBuffer | null = null;
  try {
    const axis = italic ? `ital,wght@1,${weight}` : `wght@${weight}`;
    const url =
      `https://fonts.googleapis.com/css2?family=${encodeURIComponent(family)}:${axis}` +
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

type OgFont = { name: string; data: ArrayBuffer; weight: 400 | 600 | 700; style: "normal" | "italic" };

/**
 * Fonts for one card, the three voices of Design System v2: Newsreader for the
 * headline (and its italic for a verbatim quote), Anek Latin for the reading text,
 * Geist Mono for provenance. An Indic family is added only when the text
 * needs one.
 *
 * Pass EVERY string the card draws. The subset contains exactly the glyphs you
 * ask for, so anything omitted silently disappears from the render — the first
 * cut subsetted on the headline alone and the tagline came out as "Every
 * perspective." with the space dropped.
 *
 * Returns whatever loaded; an empty array means the card renders in Satori's
 * default face rather than failing the share.
 */
export async function ogFonts(...text: string[]): Promise<OgFont[]> {
  const joined = text.join(" ");
  const all = [...new Set((joined + joined.toUpperCase() + joined.toLowerCase() + "0123456789·—–’“”").split(""))].join("");
  const indic = indicFamilyFor(all);
  const wanted: [string, number, boolean][] = [
    ["Newsreader", 600, false],
    ["Newsreader", 400, true],
    ["Anek Latin", 400, false],
    ["Anek Latin", 600, false],
    ["Geist Mono", 400, false],
    ...(indic ? ([[indic, 700, false]] as [string, number, boolean][]) : []),
  ];
  const loaded = await Promise.all(
    wanted.map(async ([family, weight, italic]) => {
      const data = await fetchFont(family, weight, all, italic);
      return data ? ({ name: family, data, weight: (weight as 400 | 600 | 700), style: italic ? "italic" : "normal" } as OgFont) : null;
    }),
  );
  return loaded.filter((f): f is OgFont => f !== null);
}

/** font-family stack for the record voice, Indic first so it wins for those glyphs. */
export function displayStack(text: string): string {
  const indic = indicFamilyFor(text);
  return [indic, "Newsreader", "Georgia", "serif"].filter(Boolean).join(", ");
}
export function bodyStack(text: string): string {
  const indic = indicFamilyFor(text);
  return [indic, "Anek Latin", "sans-serif"].filter(Boolean).join(", ");
}

export const OG_MONO = "Geist Mono, monospace";
export const OG_DISPLAY = "Newsreader, Georgia, serif";
export const OG_SANS = "Anek Latin, sans-serif";
