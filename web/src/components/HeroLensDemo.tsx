"use client";

// The flip, demonstrated on one story a general reader gets at a glance: the
// same event re-read for four kinds of reader. An ILLUSTRATION and labelled as
// one; the briefs are written, not extracted, because a professional read of
// a real story is paid and a stranger on the landing cannot fetch it. The
// mechanics are the story page's: scan line and re-ink, layout never moves,
// instant under reduced motion. Two of the four reads are marked next: they
// are being built, and the tab says so.
import Link from "next/link";
import { useState } from "react";

interface HeroLens {
  key: string;
  label: string;
  color: string;
  bg: string;
  next?: boolean;
  /** What this reading tells you, in plain words, for the unlock prompt. */
  plain: string;
  brief: string;
}

const HEADLINE = "Delhi bans diesel cars older than ten years from Monday";
// The row's label grid, beneath the headline as on the chart; no count, because
// a number inside an illustration reads as a fact two sections from a real one.
const GRID = "POL · IN";

const LENSES: HeroLens[] = [
  {
    key: "reader",
    label: "Reader",
    color: "var(--lens-general)",
    bg: "var(--lens-general-bg)",
    plain: "what happened, and what it means for you",
    brief:
      "From Monday, diesel cars registered before 2016 cannot be driven in Delhi; the transport department will impound them at checkpoints. Owners who scrap get a certificate that cuts road tax on a new car. Two-wheelers and commercial fleets are not covered yet.",
  },
  {
    key: "markets",
    label: "Markets",
    color: "var(--lens-finance)",
    bg: "var(--lens-finance-bg)",
    plain: "which companies this moves, and why",
    brief:
      "A forced replacement cycle for the capital: carmakers with petrol and CNG line-ups gain, used-car platforms lose diesel inventory overnight, and scrappage yards get a quarter of volume. Watch dealer bookings and the rebate's fine print.",
  },
  // The reads still being built flip in the neutral scale: a lens has a hue
  // once it exists as a lens, and the world has three.
  {
    key: "health",
    label: "Health",
    color: "var(--ink)",
    bg: "var(--bg-sunken)",
    next: true,
    plain: "what changes for patients and clinicians",
    brief:
      "Old diesel engines are the city's largest single source of winter particulates. Clinicians expect fewer asthma and COPD emergencies if enforcement holds through November, when the smog season starts.",
  },
  {
    key: "policy",
    label: "Policy",
    color: "var(--ink)",
    bg: "var(--bg-sunken)",
    next: true,
    plain: "what precedent this sets",
    brief:
      "The order retires vehicles by age rather than by emissions test, which the courts have not ruled on. Mumbai and Bengaluru have similar drafts waiting on how this one survives challenge.",
  },
];

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
    <div className="border" style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)" }}>
      <div className="flex items-center justify-between border-b px-5 py-3 font-mono text-[12px]" style={{ borderColor: "var(--line)", color: "var(--ink-muted)" }}>
        <span>{title}</span>
        <span style={{ color: "var(--ink-faint)" }}>Illustration</span>
      </div>

      <div className="px-5 pt-5">
        {/* A paragraph, not a heading: the demo sits inside the hero and must not break the page's outline. */}
        <p className="text-[21px] font-medium leading-[1.3] text-balance sm:text-[23px]">{HEADLINE}</p>
        <p className="mt-1.5 font-mono text-[11px] uppercase tracking-[0.04em]" style={{ color: "var(--ink-faint)" }}>{GRID}</p>
      </div>

      <div className="flex flex-wrap gap-1.5 px-5 pt-4" role="tablist" aria-label="Lens">
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
              className="flex min-h-11 items-center gap-1.5 rounded-full px-3.5 text-[13px] font-semibold transition"
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
              {l.next && <span className="font-mono text-[11px] tracking-[0.04em]" aria-label="coming next">next</span>}
            </button>
          );
        })}
      </div>

      <div key={active} className={`${flipped ? "flip-body" : ""} relative overflow-hidden px-5 pb-5 pt-4`}>
        {flipped && <span aria-hidden className="flip-scanline" style={{ background: lens.color }} />}
        {isLocked ? (
          <p className="text-[15px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
            The {lens.label} lens reads this story for {lens.plain}. It is a professional reading, so
            the brief is behind a sign-in; the flip is not.{" "}
            <Link href="/signin" className="underline underline-offset-4" style={{ color: "var(--ink)" }}>
              Sign in
            </Link>
          </p>
        ) : (
          <p className="text-[15px] leading-[1.6]" style={{ color: "var(--ink)" }}>
            <span className="font-semibold" style={{ color: lens.color }}>Through the {lens.label} lens: </span>
            {lens.brief}
          </p>
        )}
      </div>
    </div>
  );
}
