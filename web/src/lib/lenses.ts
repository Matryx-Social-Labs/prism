// Client-side lens presentation registry. The server registry
// (/api/v1/lenses, mirroring common/lenses.py) is the source of truth for
// WHICH lenses exist and their order; LENS_META carries styling for known
// slugs, and unknown future lenses get a palette fallback — so a new lens
// added on the backend renders here with no code change.

import { useEffect, useState } from "react";
import { fetchLenses } from "@/lib/api";

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

// Styling fallback for lenses the client doesn't know yet.
const FALLBACK_PALETTE: [string, string][] = [
  ["#0ea5e9", "rgba(14, 165, 233, 0.12)"],
  ["#f43f5e", "rgba(244, 63, 94, 0.12)"],
  ["#84cc16", "rgba(132, 204, 22, 0.14)"],
  ["#d946ef", "rgba(217, 70, 239, 0.12)"],
];

export function lensMeta(slug: string): LensMeta {
  return LENS_META[slug] ?? LENS_META.general;
}

export function useLenses(): LensMeta[] {
  const [lenses, setLenses] = useState<LensMeta[]>(LENS_ORDER.map((slug) => LENS_META[slug]));
  useEffect(() => {
    let cancelled = false;
    fetchLenses()
      .then((list) => {
        if (cancelled || list.length === 0) return;
        // Reader-first presentation, API order otherwise (the API leads with
        // the professional beachhead; consumers here address everyone).
        list = [...list.filter((l) => l.slug === "general"), ...list.filter((l) => l.slug !== "general")];
        setLenses(
          list.map((info, i) => {
            const known = LENS_META[info.slug];
            if (known) return { ...known, name: info.name, tagline: info.tagline };
            const [color, bg] = FALLBACK_PALETTE[i % FALLBACK_PALETTE.length];
            return {
              slug: info.slug,
              name: info.name,
              short: info.name.split(/[\s/]+/)[0],
              tagline: info.tagline,
              color,
              bg,
            };
          })
        );
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);
  return lenses;
}
