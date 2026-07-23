// Native-script short labels + English names for the launch/near-term languages.
// Single source for the feed's language-preference chip and the per-card
// headline-language tag (design v3). Codes are ISO 639-1.
export const LANG_NATIVE: Record<string, string> = {
  en: "EN", hi: "हिंदी", kn: "ಕನ್ನಡ", ta: "தமிழ்", te: "తెలుగు", bn: "বাংলা", mr: "मराठी",
};

export const LANG_NAME: Record<string, string> = {
  en: "English", hi: "Hindi", kn: "Kannada", ta: "Tamil", te: "Telugu", bn: "Bengali", mr: "Marathi",
};

export const langNative = (code: string): string => LANG_NATIVE[code] ?? code.toUpperCase();
export const langName = (code: string): string => LANG_NAME[code] ?? code.toUpperCase();
