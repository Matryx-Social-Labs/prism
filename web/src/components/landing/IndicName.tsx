"use client";

import { useEffect, useState } from "react";

/**
 * "Prism" re-set in each script Prism reads (Design System v2 · screens/Shell
 * `IndicName`), flipped in place by the lens flip's scan line. Transliterations
 * of the brand name, labelled as such. Only the languages the monitored set
 * actually reads are shown (`languages`, from /api/v1/sources); without that
 * list, or under reduced motion, it is the English name, still.
 */
const NAMES: [code: string, word: string, label: string][] = [
  ["en", "Prism", "English"],
  ["hi", "प्रिज़्म", "हिंदी"],
  ["kn", "ಪ್ರಿಸಂ", "ಕನ್ನಡ"],
  ["ta", "ப்ரிசம்", "தமிழ்"],
  ["te", "ప్రిజం", "తెలుగు"],
  ["mr", "प्रिझम", "मराठी"],
  ["bn", "প্রিজম", "বাংলা"],
  ["gu", "પ્રિઝમ", "ગુજરાતી"],
  ["ur", "پرزم", "اردو"],
];
const HOLD_MS = 1700;
const FLIP_MS = 900;
const SWAP_AT_MS = 380;

export function IndicName({ languages }: { languages: string[] | null }) {
  const names = NAMES.filter(([code]) => code === "en" || (languages ?? []).includes(code));
  const [i, setI] = useState(0);
  const [flip, setFlip] = useState(false);
  useEffect(() => {
    if (names.length < 2 || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const timers: ReturnType<typeof setTimeout>[] = [];
    const t = setInterval(() => {
      setFlip(true);
      timers.push(setTimeout(() => setI((x) => (x + 1) % names.length), SWAP_AT_MS));
      timers.push(setTimeout(() => setFlip(false), FLIP_MS));
    }, HOLD_MS + FLIP_MS);
    return () => { clearInterval(t); timers.forEach(clearTimeout); };
  }, [names.length]);
  const [code, word, label] = names[i] ?? NAMES[0];
  return (
    <span className="inline-grid gap-1.5 align-baseline" role="img" aria-label="Prism, in the scripts it reads">
      <span className="relative inline-block overflow-hidden" style={{ padding: "0.06em 0.04em 0.12em", minWidth: "3.2em" }}>
        <span
          aria-hidden
          className="inline-block text-[64px] lg:text-[104px]"
          style={{
            fontFamily: "var(--font-record)", fontWeight: 600, lineHeight: 1.08,
            letterSpacing: code === "en" ? "-0.025em" : 0, direction: code === "ur" ? "rtl" : "ltr",
            opacity: flip ? 0.12 : 1, filter: flip ? "blur(2px)" : "none",
            transition: "opacity 360ms var(--ease), filter 360ms var(--ease)",
          }}
        >
          {word}
        </span>
        {flip && <span aria-hidden className="absolute inset-x-0 h-0.5" style={{ background: "var(--accent)", boxShadow: "0 0 14px var(--accent)", animation: `sc-scan ${FLIP_MS}ms var(--ease-flip) forwards` }} />}
      </span>
      {names.length > 1 && (
        <span aria-hidden className="p-mono flex items-center gap-2 text-[12px]" style={{ color: "var(--ink-3)" }}>
          <span className="flex gap-[3px]">
            {names.map(([c], j) => <i key={c} className="h-1 transition-[width] duration-300" style={{ width: j === i ? 14 : 4, background: j === i ? "var(--ink)" : "var(--line-strong)" }} />)}
          </span>
          {label}{code !== "en" ? " · transliteration" : ""}
        </span>
      )}
    </span>
  );
}
