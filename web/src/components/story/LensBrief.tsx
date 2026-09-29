"use client";

import Link from "next/link";
import { useLayoutEffect, useRef, useState } from "react";
import { Lock } from "@/components/icons";
import { LENS_READS } from "@/lib/billing";
import { flipDuration } from "@/lib/motion";
import type { LensMeta } from "@/lib/lenses";

/** A lens's own hue, as the variables the flip and the dots read. Any lens, known or not. */
export function lensVars(meta: LensMeta): React.CSSProperties {
  return { ["--lens" as string]: meta.color, ["--lens-soft" as string]: meta.bg };
}

/**
 * "Read it as": the lenses as one segmented control (Design System v2 ·
 * LensSwitch). A professional lens carries its dot — the one place colour
 * speaks — and a lock once the reader's free readings are spent; on a desk
 * each tab prints the key that flips to it.
 */
export function LensSwitch({
  lenses,
  value,
  isLocked,
  onPick,
}: {
  lenses: LensMeta[];
  value: string;
  isLocked: (slug: string) => boolean;
  onPick: (slug: string) => void;
}) {
  return (
    <div className="flex min-w-0 flex-wrap items-center gap-x-2.5 gap-y-2">
      <span className="whitespace-nowrap text-[13px] font-semibold" style={{ color: "var(--ink-3)" }} aria-hidden>
        Read it as
      </span>
      <div className="p-hide-scroll min-w-0 max-w-full overflow-x-auto">
        <div className="p-seg" role="tablist" aria-label="Read it as">
          {lenses.map((m, i) => {
            const on = m.slug === value;
            const locked = isLocked(m.slug);
            return (
              <button
                key={m.slug}
                type="button"
                role="tab"
                aria-selected={on}
                onClick={() => onPick(m.slug)}
                aria-label={locked ? `${m.short} lens, free readings spent` : undefined}
                className="min-h-[44px] whitespace-nowrap lg:min-h-[38px]"
                style={{ ...lensVars(m), color: on ? "var(--ink)" : "var(--ink-2)" }}
              >
                {m.slug !== "reader" && <i aria-hidden className="inline-block h-2 w-2 rounded-full" style={{ background: "var(--lens)" }} />}
                {m.short}
                {locked && <Lock size={12} />}
                <kbd className="p-kbd ml-0.5 hidden lg:inline" aria-hidden>{i + 1}</kbd>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}

/**
 * The lens block (Design System v2 · LensBrief): a surface under a 2px rule
 * in the lens's hue, a label and what this reading is, then the body. The
 * flip is the one signature motion: when the reader picks a lens the block
 * mounts again and a scan line in the lens hue sweeps it while the text
 * re-inks behind it, paced by the block's height, never a crossfade. Reduced
 * motion swaps in place (globals.css).
 */
export function LensBrief({
  meta,
  flip,
  intro,
  children,
}: {
  meta: LensMeta;
  /** Animate on mount: true for every block after the first the reader picked. */
  flip: boolean;
  intro: string;
  children: React.ReactNode;
}) {
  const ref = useRef<HTMLElement>(null);
  const [flipping, setFlipping] = useState(false);
  const pro = meta.slug !== "reader";
  // The clock is the new block's height, measured before it paints.
  useLayoutEffect(() => {
    const el = ref.current;
    if (!flip || !el) return;
    const ms = flipDuration(el.offsetHeight);
    el.style.setProperty("--flip-ms", `${ms}ms`);
    setFlipping(true);
    const t = window.setTimeout(() => setFlipping(false), ms + 40);
    return () => window.clearTimeout(t);
  }, [flip]);
  return (
    <section
      ref={ref}
      aria-labelledby="brief-title"
      className={`p-flip relative grid gap-3 overflow-hidden px-4 pb-[18px] pt-3.5 sm:px-[18px] ${flipping ? "is-flipping" : ""}`}
      style={{
        ...lensVars(meta),
        borderTop: `2px solid ${pro ? "var(--lens)" : "var(--ink)"}`,
        background: pro ? "color-mix(in srgb, var(--lens-soft) 55%, var(--surface))" : "var(--surface)",
        borderRadius: "0 0 var(--r-lg) var(--r-lg)",
        color: "var(--ink)",
      }}
    >
      <span className="p-flip__scan" aria-hidden />
      <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
        {pro && <i aria-hidden className="inline-block h-2 w-2 self-center rounded-full" style={{ background: "var(--lens)" }} />}
        <h2 id="brief-title" className="whitespace-nowrap text-[13px] font-semibold leading-none" style={{ color: pro ? "var(--lens)" : "var(--ink)" }}>
          {pro ? `${meta.short} read` : "The brief"}
        </h2>
        <p className="min-w-0 text-[13px] leading-[1.35] sm:ml-auto sm:text-right" style={{ color: "var(--ink-3)" }}>{intro}</p>
      </div>
      {children}
    </section>
  );
}

/** Writing: counted skeleton lines while the reading is generated. */
export function LensWriting({ meta }: { meta: LensMeta }) {
  return (
    <div className="grid gap-2" aria-label="Generating lens brief">
      <span className="p-count">Writing the {meta.short} read of this story…</span>
      <span className="p-skel h-3.5 w-[92%]" />
      <span className="p-skel h-3.5 w-[80%]" />
      <span className="p-skel h-3.5 w-[86%]" />
    </div>
  );
}

/** Locked: out of the reads open without an account. What the lens reads,
 *  blurred placeholder lines, what an account gives, and Plus — whose page
 *  brings the reader back to `back`, the story they were on. */
export function LensLocked({ meta, used, back, onSignIn }: { meta: LensMeta; used: number | null; back: string; onSignIn: () => void }) {
  return (
    <div className="grid gap-3">
      <div aria-hidden className="grid select-none gap-2 opacity-55 blur-[4px]">
        {["90%", "76%", "84%"].map((w) => <span key={w} className="block h-3 rounded-[2px]" style={{ width: w, background: "var(--lens)", opacity: 0.25 }} />)}
      </div>
      <p className="text-[15px] font-semibold leading-[1.4]">{LENS_READS.free} lens readings a day with a free account</p>
      <p className="-mt-2 text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
        {used != null && `You have read ${used} without one. `}
        Read this story through the <span className="font-semibold" style={{ color: "var(--lens)" }}>{meta.short} lens</span>: {meta.plain ?? meta.tagline}.
      </p>
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <button type="button" onClick={onSignIn} className="p-btn p-btn--primary p-btn--sm">Sign in to keep reading</button>
        <Link href={`/plus?from=lens-signin&next=${encodeURIComponent(back)}`} className="text-[14px] font-semibold" style={{ color: "var(--accent)" }}>Every lens with Plus →</Link>
      </div>
    </div>
  );
}

/** Used: a free account's readings for the day are spent — a different wall
 *  from not signed in, and the one Plus answers: in place, over the story
 *  (the upgrade sheet), never a trip away from the lens they wanted. */
export function LensUsed({ used, limit, onPlus, onReader }: { used: number | null; limit: number | null; onPlus: () => void; onReader: () => void }) {
  const cap = limit ?? LENS_READS.free;
  return (
    <div className="grid gap-2.5">
      <p className="text-[15px] font-semibold leading-[1.4]">You have read {used ?? cap} of {cap} free lens readings today</p>
      <p className="text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>
        Plus opens every lens on every story. The reader view of this story stays open, with its sources and quotes.
      </p>
      <div className="flex flex-wrap items-center gap-2.5">
        <button type="button" onClick={onPlus} className="p-btn p-btn--primary p-btn--sm">Get Plus</button>
        <button type="button" onClick={onReader} className="p-btn p-btn--secondary p-btn--sm">Back to the reader view</button>
      </div>
    </div>
  );
}
