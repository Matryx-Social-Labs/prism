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
  // Plain-language "what this lens tells you", for prose read by people who
  // aren't from that profession. `name` ("Cybersecurity / GRC") and `tagline`
  // ("CVEs … your controls") are role-targeted jargon — right as picker labels
  // for a pro scanning for their own row, wrong in a sentence aimed at
  // everyone. Optional: lenses the client doesn't know fall back to `tagline`.
  plain?: string;
  color: string; // CSS var reference
  bg: string;
}

export const LENS_META: Record<string, LensMeta> = {
  reader: {
    slug: "reader",
    name: "General reader",
    short: "Reader",
    tagline: "Every story with every perspective, consequences, and answers",
    plain: "what happened, and why it matters",
    color: "var(--ink)", // the record is neutral: the Reader lens has no hue
    bg: "var(--sunken)",
  },
  cyber: {
    slug: "cyber",
    name: "Cybersecurity / GRC",
    short: "Cyber",
    tagline: "CVEs, incidents, and what they mean for your controls",
    plain: "who's exposed by this, and what to fix first",
    color: "var(--lens-cyber)",
    bg: "var(--lens-cyber-soft)",
  },
  markets: {
    slug: "markets",
    name: "Finance / Trader",
    short: "Markets",
    tagline: "Market-moving news with tickers, catalysts, and price reads",
    plain: "what this moves in the market, and why",
    color: "var(--lens-markets)",
    bg: "var(--lens-markets-soft)",
  },
};

export const LENS_ORDER = ["reader", "cyber", "markets"];

// Styling for lenses the client doesn't know yet: the next unused stops of the
// spectrum (DESIGN.md § Lenses — health rose, policy amber), then a repeat.
const FALLBACK_PALETTE: [string, string][] = [
  ["var(--lens-health)", "var(--lens-health-soft)"],
  ["var(--lens-policy)", "var(--lens-policy-soft)"],
  ["var(--lens-cyber)", "var(--lens-cyber-soft)"],
  ["var(--lens-markets)", "var(--lens-markets-soft)"],
];

export function lensMeta(slug: string): LensMeta {
  return LENS_META[slug] ?? LENS_META.reader;
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
        list = [...list.filter((l) => l.slug === "reader"), ...list.filter((l) => l.slug !== "reader")];
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
