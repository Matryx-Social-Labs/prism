// Client-side lens presentation registry (mirrors common/lenses.py slugs).

export interface LensMeta {
  slug: string;
  name: string;
  short: string;
  tagline: string;
  color: string; // CSS var reference
  bg: string;
}

export const LENS_META: Record<string, LensMeta> = {
  general: {
    slug: "general",
    name: "General reader",
    short: "Reader",
    tagline: "Every story with both sides, consequences, and answers",
    color: "var(--lens-general)",
    bg: "var(--lens-general-bg)",
  },
  cyber_grc: {
    slug: "cyber_grc",
    name: "Cybersecurity / GRC",
    short: "Cyber",
    tagline: "CVEs, incidents, and what they mean for your controls",
    color: "var(--lens-cyber)",
    bg: "var(--lens-cyber-bg)",
  },
  finance_trader: {
    slug: "finance_trader",
    name: "Finance / Trader",
    short: "Markets",
    tagline: "Market-moving news with tickers, catalysts, and price reads",
    color: "var(--lens-finance)",
    bg: "var(--lens-finance-bg)",
  },
};

export const LENS_ORDER = ["general", "cyber_grc", "finance_trader"];

export function lensMeta(slug: string): LensMeta {
  return LENS_META[slug] ?? LENS_META.general;
}
