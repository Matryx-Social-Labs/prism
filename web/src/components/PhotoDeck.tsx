"use client";

import { useEffect, useRef, useState } from "react";
import { OutletIcon } from "@/components/Coverage";
import { ArrowLeft, ArrowRight, ArrowUpRight } from "@/components/icons";
import { fallbackCode } from "@/lib/sources";
import type { SourceRef } from "@/lib/api";
import { relativeTime } from "@/lib/dateline";
import { REPORT_IMAGES } from "@/lib/images";
import { framesFromSources, type DeckPhoto } from "@/lib/photos";

// The record's photographs (DESIGN.md § Images): one stage showing one
// outlet's picture at a time, the others fanned behind it as a stack — the
// picture of a corroborated story is many pictures — a filmstrip of the rest
// under it on a desk, native swipe on the phone. Every frame is CREDITED on
// the image and opens the report it came from; the stage never advances on
// its own; arrows and the keyboard step it; the count is printed as a count.
// Motion is the browser's own scroll-snap (240ms smooth, instant under
// reduced motion) — never a crossfade.
export function PhotoDeck({ sources, frames }: { sources?: SourceRef[]; frames?: DeckPhoto[] }) {
  const photos: DeckPhoto[] = REPORT_IMAGES ? (frames ?? framesFromSources(sources ?? [])) : [];
  const stage = useRef<HTMLUListElement>(null);
  const [i, setI] = useState(0);
  const [dead, setDead] = useState<Set<string>>(new Set());
  const live = photos.filter((p) => !dead.has(p.key));
  const n = live.length;

  // Which frame is in view, from the browser's own scroll position.
  useEffect(() => {
    const el = stage.current;
    if (!el) return;
    const onScroll = () => setI(Math.round(el.scrollLeft / Math.max(1, el.clientWidth)));
    el.addEventListener("scroll", onScroll, { passive: true });
    return () => el.removeEventListener("scroll", onScroll);
  }, [n]);

  if (n === 0) return null;
  const go = (k: number) => {
    const el = stage.current;
    if (!el) return;
    const next = (k + n) % n;
    el.scrollTo({ left: next * el.clientWidth, behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth" });
    setI(next);
  };
  const cur = live[Math.min(i, n - 1)];

  return (
    <figure className="relative" aria-label={`Photographs from the reports, ${n} of them`}>
      {/* The stack: the pictures behind the one you are looking at. */}
      {n > 1 && (
        <>
          <span aria-hidden className="absolute inset-x-3 -top-2 h-6 rounded-[var(--r-md)] border" style={{ borderColor: "var(--line)", background: "var(--surface)", transform: "rotate(-1.2deg)" }} />
          {n > 2 && <span aria-hidden className="absolute inset-x-6 -top-3.5 h-6 rounded-[var(--r-md)] border" style={{ borderColor: "var(--line)", background: "var(--sunken)", transform: "rotate(1.4deg)" }} />}
        </>
      )}
      <div className="relative overflow-hidden rounded-[var(--r-md)] border" style={{ borderColor: "var(--line)", background: "var(--sunken)" }}>
        <ul
          ref={stage}
          className="hide-scroll flex snap-x snap-mandatory overflow-x-auto"
          aria-live="polite"
          onKeyDown={(e) => { if (e.key === "ArrowRight") go(i + 1); if (e.key === "ArrowLeft") go(i - 1); }}
          tabIndex={n > 1 ? 0 : -1}
        >
          {live.map((s, k) => (
            <li key={s.key} className="relative aspect-[16/10] w-full flex-none snap-center lg:aspect-[2/1]" aria-hidden={k !== i} aria-label={`${k + 1} of ${n}: ${s.source_name}`}>
              <a href={s.url} target="_blank" rel="noopener noreferrer" className="block h-full w-full" tabIndex={k === i ? 0 : -1} aria-label={`Open the report at ${s.source_name}${s.title ? `: ${s.title}` : ""}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={s.image_url}
                  alt={`Photo from ${s.source_name}`}
                  loading={k === 0 ? "eager" : "lazy"}
                  decoding="async"
                  referrerPolicy="no-referrer"
                  className="h-full w-full object-cover"
                  onError={() => setDead((d) => new Set(d).add(s.key))}
                />
              </a>
            </li>
          ))}
        </ul>
        {/* The credit, on the image, for the frame in view. */}
        <div className="pointer-events-none absolute inset-x-0 bottom-0 flex items-center gap-2 px-3 pb-2.5 pt-10 text-[12.5px] font-semibold text-white" style={{ background: "linear-gradient(to top, rgba(0,0,0,.78) 0%, rgba(0,0,0,.45) 55%, rgba(0,0,0,0) 100%)", textShadow: "0 1px 2px rgba(0,0,0,.5)" }}>
          <OutletIcon domain={cur.domain} code={cur.code ?? fallbackCode(cur.source_name)} name={cur.source_name} size={20} />
          <span className="truncate">Photo: {cur.source_name}</span>
          {cur.published_at && <span className="shrink-0 font-mono text-[10.5px] font-normal opacity-90">{relativeTime(cur.published_at)}</span>}
          <a href={cur.url} target="_blank" rel="noopener noreferrer" className="pointer-events-auto ml-auto inline-flex shrink-0 items-center gap-1 font-mono text-[10.5px] font-normal underline-offset-2 hover:underline">
            Open report <ArrowUpRight size={11} />
          </a>
        </div>
        {n > 1 && (
          <>
            <button type="button" onClick={() => go(i - 1)} aria-label="Previous photograph" className="absolute left-2 top-1/2 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full lg:grid" style={{ background: "rgba(255,255,255,.9)", color: "var(--ink)", boxShadow: "var(--shadow-1)" }}><ArrowLeft size={16} /></button>
            <button type="button" onClick={() => go(i + 1)} aria-label="Next photograph" className="absolute right-2 top-1/2 hidden h-11 w-11 -translate-y-1/2 place-items-center rounded-full lg:grid" style={{ background: "rgba(255,255,255,.9)", color: "var(--ink)", boxShadow: "var(--shadow-1)" }}><ArrowRight size={16} /></button>
            <span className="absolute right-2.5 top-2.5 rounded-full px-2 py-0.5 font-mono text-[11px] tabular-nums text-white" style={{ background: "rgba(0,0,0,.55)" }} aria-hidden>{Math.min(i, n - 1) + 1} / {n}</span>
          </>
        )}
      </div>
      {/* The filmstrip: every picture, one tap away, on a desk. */}
      {n > 1 && (
        <ol className="mt-2 hidden gap-1.5 lg:flex" aria-label="All photographs">
          {live.map((s, k) => (
            <li key={s.key}>
              <button type="button" onClick={() => go(k)} aria-label={`Photograph ${k + 1}, ${s.source_name}`} aria-current={k === i ? "true" : undefined} className="block h-[42px] w-[60px] overflow-hidden rounded-[6px] border transition-opacity" style={{ borderColor: k === i ? "var(--ink)" : "var(--line)", opacity: k === i ? 1 : 0.7 }}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={s.image_url} alt="" loading="lazy" decoding="async" referrerPolicy="no-referrer" className="h-full w-full object-cover" />
              </button>
            </li>
          ))}
        </ol>
      )}
      <figcaption className="mt-2 font-mono text-[11px] uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
        From the reports · {n} {n === 1 ? "photo" : "photos"}
      </figcaption>
    </figure>
  );
}
