"use client";

import Link from "next/link";
import { useLayoutEffect, useRef, useState } from "react";
import { Lock } from "@/components/icons";
import { useLenses } from "@/lib/lenses";
import { flipDuration } from "@/lib/motion";
import { sentences } from "@/lib/sentences";
import { useSession } from "@/lib/session";

/**
 * The lens flip on one real story (Design System v2 · LensSwitch + LensBrief):
 * the lenses the story offers, from the live registry; the Reader brief and
 * what to watch as the record printed them. A professional reading is behind a
 * sign-in for a signed-out reader, exactly as on the story page, so its lens
 * flips to the unlock prompt rather than to a written sample. The flip is the
 * scan line and re-ink (`.p-flip`), paced by the block's height; instant under
 * reduced motion.
 */
const BRIEF_SENTENCES = 2;
const WATCH_POINTS = 3;

export type LensStory = { id: string; title: string; reports: number; brief: string; points: string[]; available: string[] };

export function LensFlip({ story }: { story: LensStory }) {
  const registry = useLenses();
  const offered = story.available.length ? registry.filter((l) => story.available.includes(l.slug)) : registry;
  const session = useSession();
  const [slug, setSlug] = useState("reader");
  const [flipping, setFlipping] = useState(false);
  const ref = useRef<HTMLElement>(null);
  const shown = useRef(slug);

  useLayoutEffect(() => {
    // Flip only on a change of lens, never on mount (nor on StrictMode's re-run of it).
    if (shown.current === slug) return;
    shown.current = slug;
    const el = ref.current;
    if (!el || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const ms = flipDuration(el.offsetHeight);
    el.style.setProperty("--flip-ms", `${ms}ms`);
    setFlipping(false);
    const raf = requestAnimationFrame(() => setFlipping(true));
    const t = setTimeout(() => setFlipping(false), ms + 40);
    return () => { cancelAnimationFrame(raf); clearTimeout(t); };
  }, [slug]);

  const meta = offered.find((l) => l.slug === slug) ?? offered[0];
  if (!meta) return null;
  const pro = meta.slug !== "reader";
  // The brief's opening, as written; the rest is one tap away on the story.
  const all = sentences(story.brief);
  const opening = all.slice(0, BRIEF_SENTENCES).join(" ");
  const label = meta.short ?? meta.name;

  return (
    <div className="grid min-w-0 gap-4">
      <div className="flex flex-wrap items-center gap-2.5">
        <span className="whitespace-nowrap text-[13px] font-semibold" style={{ color: "var(--ink-3)" }}>Read it as</span>
        <div className="p-seg max-w-full overflow-x-auto p-hide-scroll" role="tablist" aria-label="Lens">
          {offered.map((l) => {
            const on = l.slug === meta.slug;
            return (
              <button key={l.slug} type="button" role="tab" id={`lens-tab-${l.slug}`} aria-selected={on} aria-controls="lens-brief" onClick={() => setSlug(l.slug)} className="shrink-0" style={{ color: on ? "var(--ink)" : "var(--ink-2)", minHeight: 44 }}>
                {l.slug !== "reader" && <i aria-hidden className="inline-block h-2 w-2 rounded-full" style={{ background: l.color }} />}
                {l.short ?? l.name}
                {l.slug !== "reader" && !session && <Lock size={12} className="opacity-70" />}
              </button>
            );
          })}
        </div>
      </div>

      <section
        ref={ref}
        id="lens-brief"
        role="tabpanel"
        aria-labelledby={`lens-tab-${meta.slug}`}
        className={`p-flip grid gap-2.5 ${flipping ? "is-flipping" : ""}`}
        style={{
          "--lens": meta.color,
          borderTop: `2px solid ${pro ? meta.color : "var(--ink)"}`,
          background: pro ? `color-mix(in srgb, ${meta.bg} 55%, var(--surface))` : "var(--surface)",
          padding: "14px 18px 18px",
          borderRadius: "0 0 var(--r-lg) var(--r-lg)",
          color: "var(--ink)",
        } as React.CSSProperties}
      >
        <span className="p-flip__scan" />
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
          {pro && <i aria-hidden className="inline-block h-2 w-2 rounded-full" style={{ background: meta.color }} />}
          <span className="whitespace-nowrap text-[13px] font-semibold" style={{ color: pro ? meta.color : "var(--ink)" }}>{pro ? `${label} read` : "The brief"}</span>
          <span className="ml-auto text-[13px] leading-[1.35]" style={{ color: "var(--ink-3)" }}>
            {pro ? `The same reports, read for ${label.toLowerCase()}.` : `Written by software from the ${story.reports} ${story.reports === 1 ? "report" : "reports"} on this story.`}
          </span>
        </div>
        {!pro ? (
          <div className="grid gap-3">
            <p style={{ font: "var(--t-body-l)" }}>
              {opening}
              {all.length > BRIEF_SENTENCES && <> <Link href={`/story/${story.id}`} className="p-link whitespace-nowrap" style={{ font: "600 15px/1 var(--font-read)", color: "var(--accent)" }}>The whole brief</Link></>}
            </p>
            {story.points.length > 0 && (
              <div>
                <p className="p-eyebrow mb-1.5">What to watch</p>
                <ul className="grid gap-1.5">
                  {story.points.slice(0, WATCH_POINTS).map((p) => (
                    <li key={p} className="grid grid-cols-[14px_1fr] gap-2" style={{ font: "var(--t-body-s)" }}>
                      <span aria-hidden className="mt-[9px] h-1.5 w-1.5" style={{ background: "var(--ink)" }} />
                      {p}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
        ) : session ? (
          <div className="grid justify-items-start gap-3">
            <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>The {label} reading of this story is on the story itself.</p>
            <Link href={`/story/${story.id}`} className="p-btn p-btn--primary">Read it on the story</Link>
          </div>
        ) : (
          <div className="grid justify-items-start gap-3">
            <div aria-hidden className="grid w-full select-none gap-2" style={{ filter: "blur(4px)", opacity: 0.55 }}>
              {["90%", "76%", "84%"].map((w) => <span key={w} className="h-3 rounded-[2px]" style={{ width: w, background: meta.color, opacity: 0.25 }} />)}
            </div>
            <p className="text-[15px] font-semibold leading-[1.4]">Free with an account</p>
            <p className="-mt-2" style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>The {label} reading of this story: {meta.plain ?? meta.tagline}.</p>
            <Link href={`/signin?next=/story/${story.id}`} className="p-btn p-btn--primary">Sign in to unlock</Link>
          </div>
        )}
      </section>
    </div>
  );
}
