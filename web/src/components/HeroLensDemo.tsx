"use client";

// The flip, demonstrated: one story re-read through four lenses, two of them
// drafted and not yet served. Illustrative on the about page (the story is an
// example, not a record); the real product lens set is whatever /api/v1/lenses
// returns. Mechanics are the story page's: scan line and re-ink, layout never
// moves, instant under reduced motion.
import Link from "next/link";
import { useState } from "react";

interface HeroLens {
  key: string;
  label: string;
  color: string;
  bg: string;
  /** What this reading tells you, in plain words, for the unlock prompt. */
  plain: string;
  brief: string;
}

const LENSES: HeroLens[] = [
  {
    key: "reader",
    label: "Reader",
    color: "var(--lens-general)",
    bg: "var(--lens-general-bg)",
    plain: "what happened, and why it matters",
    brief:
      "The patent office cleared three manufacturers to make semaglutide from January, with prices projected to fall up to 80%. Two narratives are already competing, a public-health milestone against patent erosion, and both are grouped on the story page.",
  },
  {
    key: "markets",
    label: "Markets",
    color: "var(--lens-finance)",
    bg: "var(--lens-finance-bg)",
    plain: "which tickers move, and what the catalyst is",
    brief:
      "Generics names (SUNPHARMA, CIPLA, DRREDDY) catch a bid on volume upside while the innovator faces price erosion in its fastest-growing market. Watch API-capacity announcements and the innovator's India revenue guidance.",
  },
  {
    key: "health",
    label: "Health",
    // Reserved hues (DESIGN.md) have no tokens yet, so the tint is mixed from
    // the hue itself and reads the same on both grounds.
    color: "#be123c",
    bg: "color-mix(in srgb, #be123c 14%, transparent)",
    plain: "what changes for clinicians and patients",
    brief:
      "Prescribing will widen beyond endocrinology once prices fall; the immediate clinical questions are supply consistency and cold-chain reliability outside metros.",
  },
  {
    key: "policy",
    label: "Policy",
    color: "#0369a1",
    bg: "color-mix(in srgb, #0369a1 14%, transparent)",
    plain: "what precedent this sets",
    brief:
      "The ruling becomes a reference point for compulsory-licensing and access-to-medicine arguments; expect it cited well beyond pharma, including in trade negotiations.",
  },
];

const MONO = "font-mono text-[10.5px] uppercase tracking-[0.06em]";

export function HeroLensDemo({
  locked = [],
  title = "Flip the lens",
}: {
  /** Lenses that flip but show the unlock prompt instead of the reading: the paywall moment. */
  locked?: string[];
  /** The instruction printed above the demo. */
  title?: string;
}) {
  const [active, setActive] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const lens = LENSES[active];
  const isLocked = locked.includes(lens.key);

  return (
    <div className="border" style={{ borderColor: "var(--line)", background: "var(--bg-elevated)" }}>
      <div className={`${MONO} flex items-center justify-between border-b px-5 py-3`} style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
        <span>{title}</span>
        <span style={{ color: "var(--ink-faint)" }}>Illustration</span>
      </div>

      <h3 className="px-5 pt-4 text-[18px] font-medium leading-[1.3] text-balance">
        Blockbuster obesity drug goes generic in India after landmark patent ruling
      </h3>

      <div className="flex flex-wrap gap-1.5 px-5 pt-3.5" role="tablist" aria-label="Lens">
        {LENSES.map((l, i) => {
          const selected = i === active;
          const lock = locked.includes(l.key);
          return (
            <button
              key={l.key}
              role="tab"
              aria-selected={selected}
              aria-label={lock ? `${l.label} lens, locked` : undefined}
              onClick={() => {
                setFlipped(true);
                setActive(i);
              }}
              className="flex min-h-[36px] items-center gap-1 rounded-full px-3.5 text-xs font-semibold transition"
              style={
                selected
                  ? { background: l.bg, color: l.color, boxShadow: `inset 0 0 0 1.5px ${l.color}` }
                  : { color: lock ? "var(--ink-faint)" : "var(--ink-muted)" }
              }
            >
              {lock && (
                <svg aria-hidden width="10" height="10" viewBox="0 0 24 24" fill="none" style={{ opacity: 0.75 }}>
                  <rect x="5" y="11" width="14" height="9" rx="2" stroke="currentColor" strokeWidth="2.2" />
                  <path d="M8 11V8a4 4 0 0 1 8 0v3" stroke="currentColor" strokeWidth="2.2" />
                </svg>
              )}
              {l.label}
            </button>
          );
        })}
      </div>

      <div key={active} className={`${flipped ? "flip-body" : ""} relative overflow-hidden px-5 pb-5 pt-4`}>
        {flipped && <span aria-hidden className="flip-scanline" style={{ background: lens.color }} />}
        <p className={MONO} style={{ color: lens.color }}>
          {lens.label} read
        </p>
        {isLocked ? (
          <p className="mt-2 text-[14px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            The {lens.label} lens reads this story for {lens.plain}. It is a professional reading, so
            the brief is behind a sign-in; the flip is not.{" "}
            <Link href="/signin" className="underline underline-offset-4" style={{ color: "var(--ink)" }}>
              Sign in
            </Link>
          </p>
        ) : (
          <p className="mt-2 text-[14px] leading-[1.6]" style={{ color: "var(--ink)" }}>
            {lens.brief}
          </p>
        )}
      </div>
    </div>
  );
}
