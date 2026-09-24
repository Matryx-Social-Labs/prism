// Native-script short labels + English names for the launch/near-term languages.
// Single source for the feed's language-preference chip and the per-card
// headline-language tag (design v3). Codes are ISO 639-1.
// Every language Prism INGESTS, not only the ones the picker offers: quotes now
// carry the language the article printed them in, and a Punjabi quote labelled
// "PA" reads as a code rather than a language. `coverage.ts` reads this registry
// too — it used to keep a second, longer copy of the same map, and the shorter
// one was the one the chips rendered from.
export const LANG_NATIVE: Record<string, string> = {
  en: "EN", hi: "हिंदी", kn: "ಕನ್ನಡ", ta: "தமிழ்", te: "తెలుగు", bn: "বাংলা", mr: "मराठी",
  gu: "ગુજરાતી", pa: "ਪੰਜਾਬੀ", ur: "اردو", ml: "മലയാളം", or: "ଓଡ଼ିଆ", as: "অসমীয়া",
};

export const LANG_NAME: Record<string, string> = {
  en: "English", hi: "Hindi", kn: "Kannada", ta: "Tamil", te: "Telugu", bn: "Bengali", mr: "Marathi",
  gu: "Gujarati", pa: "Punjabi", ur: "Urdu", ml: "Malayalam", or: "Odia", as: "Assamese", ar: "Arabic", ru: "Russian",
};

export const langNative = (code: string): string => LANG_NATIVE[code] ?? code.toUpperCase();
export const langName = (code: string): string => LANG_NAME[code] ?? code.toUpperCase();

// Fallback when the API doesn't tag a headline's language: infer it from the
// script. Covers the launch Indian languages (each has a distinct Unicode block);
// returns null for Latin script (treated as English/unknown, no tag). Devanagari
// maps to Hindi — it's also Marathi's script, but Hindi is the common label.
const SCRIPT_RANGES: [RegExp, string][] = [
  [/[ऀ-ॿ]/, "hi"], // Devanagari
  [/[ಀ-೿]/, "kn"], // Kannada
  [/[஀-௿]/, "ta"], // Tamil
  [/[ఀ-౿]/, "te"], // Telugu
  [/[ঀ-৿]/, "bn"], // Bengali
];

export function detectScript(text: string): string | null {
  for (const [re, lang] of SCRIPT_RANGES) if (re.test(text)) return lang;
  return null;
}
