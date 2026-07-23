"use client";

// Landing hero flip demo — the exact 2a mockup content: one obesity-drug story
// re-read across four lenses (two of them upcoming). Static/illustrative on the
// marketing page; the real product lens set stays Reader/Cyber/Markets.
import { useState } from "react";

interface HeroLens {
  key: string;
  label: string;
  color: string;
  bg: string;
  brief: string;
}

const LENSES: HeroLens[] = [
  {
    key: "reader",
    label: "Reader",
    color: "var(--lens-general)",
    bg: "var(--lens-general-bg)",
    brief:
      "the patent office cleared three manufacturers to make semaglutide from January, with prices projected to fall up to 80%. Two narratives are already competing — a public-health milestone versus patent erosion — and both are grouped on the story page.",
  },
  {
    key: "markets",
    label: "Markets",
    color: "var(--lens-finance)",
    bg: "var(--lens-finance-bg)",
    brief:
      "generics names ($SUNPHARMA, $CIPLA, $DRREDDY) catch a bid on volume upside while the innovator faces price erosion in its fastest-growing market. Watch API-capacity announcements and the innovator's India revenue guidance.",
  },
  {
    key: "health",
    label: "Health",
    color: "#be123c",
    bg: "#ffe4e6",
    brief:
      "prescribing will widen beyond endocrinology once prices fall; the immediate clinical questions are supply consistency and cold-chain reliability outside metros.",
  },
  {
    key: "policy",
    label: "Policy",
    color: "#0369a1",
    bg: "#e0f2fe",
    brief:
      "the ruling becomes a reference point for compulsory-licensing and access-to-medicine arguments — expect it cited well beyond pharma, including in trade negotiations.",
  },
];

export function HeroLensDemo() {
  const [active, setActive] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const lens = LENSES[active];

  return (
    <div
      className="overflow-hidden rounded-[18px] border"
      style={{ borderColor: "var(--line)", background: "var(--bg-elevated)", boxShadow: "var(--shadow-pop)" }}
    >
      <div className="flex items-center justify-between border-b px-5 py-3" style={{ borderColor: "var(--line)" }}>
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
          Try it — flip the lens
        </span>
        <span className="spectrum-bar h-1 w-16 rounded-full" aria-hidden />
      </div>

      <div className="px-5 pt-4">
        <h3 className="text-[18px] font-semibold leading-[1.35]" style={{ fontFamily: "var(--font-display), serif" }}>
          Blockbuster obesity drug goes generic in India after landmark patent ruling
        </h3>
      </div>

      <div className="flex flex-wrap gap-1.5 px-5 pt-3.5" role="tablist" aria-label="Lens">
        {LENSES.map((l, i) => {
          const selected = i === active;
          return (
            <button
              key={l.key}
              role="tab"
              aria-selected={selected}
              onClick={() => {
                setFlipped(true);
                setActive(i);
              }}
              className="rounded-full px-3.5 py-1.5 text-xs font-semibold transition"
              style={
                selected
                  ? { background: l.bg, color: l.color, boxShadow: `inset 0 0 0 1.5px ${l.color}` }
                  : { color: "var(--ink-muted)" }
              }
            >
              {l.label}
            </button>
          );
        })}
      </div>

      <div key={active} className={`${flipped ? "flip-body" : ""} relative overflow-hidden px-5 pb-4 pt-3`}>
        {flipped && <span aria-hidden className="flip-scanline" style={{ background: lens.color }} />}
        <p className="text-[13px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
          <span className="font-semibold" style={{ color: lens.color }}>
            Through the {lens.label} lens —{" "}
          </span>
          {lens.brief}
        </p>
      </div>

      <p className="px-5 pb-4 text-[11px]" style={{ color: "var(--ink-faint)" }}>
        Health and Policy are upcoming lenses — new roles ship as registry entries, not new products.
      </p>
    </div>
  );
}
