"use client";

import { useEffect, useRef, useState } from "react";
import { OutletIcon } from "@/components/Coverage";
import { PhotoImg } from "@/components/PhotoImg";
import { ArrowLeft, ArrowRight } from "@/components/icons";
import { fallbackCode } from "@/lib/sources";
import type { SourceRef } from "@/lib/api";
import { REPORT_IMAGES } from "@/lib/images";
import { framesFromSources, type DeckPhoto } from "@/lib/photos";

/**
 * The record's photographs (Design System v2 · PhotoDeck; guidelines/motion):
 * publishers' photos as credited previews of their own reports, never Prism's
 * image. One on the stage, the next two peeking behind it. Advancing, the front
 * photo leaves sideways with a 5° tilt and fades while the next rises from 94%
 * to full size (480ms, cubic-bezier(.2,.8,.2,1)); a drag follows the finger
 * with 1° of tilt per 40px, and a release past 60px advances, otherwise it
 * springs back. Arrow keys and the thumbnails step it. The credit rides on the
 * photo. Nothing advances on its own; reduced motion swaps in place.
 */
const PEEK = [{ x: 0, s: 1, o: 1 }, { x: 16, s: 0.94, o: 0.9 }, { x: 30, s: 0.88, o: 0.7 }];
const ADVANCE_MS = 480;
const DRAG_ADVANCE_PX = 60;
const PX_PER_DEGREE = 40;

function useReduced(): boolean {
  const [r, setR] = useState(false);
  useEffect(() => setR(window.matchMedia("(prefers-reduced-motion: reduce)").matches), []);
  return r;
}

export function PhotoDeck({ sources, frames }: { sources?: SourceRef[]; frames?: DeckPhoto[] }) {
  const photos: DeckPhoto[] = REPORT_IMAGES ? (frames ?? framesFromSources(sources ?? [])) : [];
  const reduced = useReduced();
  const [dead, setDead] = useState<ReadonlySet<string>>(new Set());
  const live = photos.filter((p) => !dead.has(p.key));
  const n = live.length;
  const [at, setAt] = useState(0);
  const [leaving, setLeaving] = useState<{ key: string; dir: 1 | -1 } | null>(null);
  const [drag, setDrag] = useState<{ x0: number; dx: number } | null>(null);
  const timer = useRef<number | null>(null);
  useEffect(() => () => { if (timer.current) window.clearTimeout(timer.current); }, []);

  if (n === 0) return null;
  const i = Math.min(at, n - 1);
  const cur = live[i];

  const show = (next: number, dir: 1 | -1) => {
    if (n < 2) return;
    const to = (next + n) % n;
    if (to === i) return;
    setLeaving({ key: cur.key, dir });
    setAt(to);
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setLeaving(null), reduced ? 0 : ADVANCE_MS);
  };
  const go = (dir: 1 | -1) => show(i + dir, dir);

  const onDown = (e: React.PointerEvent<HTMLDivElement>) => {
    if (n < 2 || e.button !== 0) return;
    e.currentTarget.setPointerCapture?.(e.pointerId);
    setDrag({ x0: e.clientX, dx: 0 });
  };
  const onMove = (e: React.PointerEvent<HTMLDivElement>) => { if (drag) setDrag({ ...drag, dx: e.clientX - drag.x0 }); };
  const onUp = () => {
    if (!drag) return;
    const dx = drag.dx;
    setDrag(null);
    if (dx < -DRAG_ADVANCE_PX) go(1);
    else if (dx > DRAG_ADVANCE_PX) go(-1);
  };
  const transition = reduced || drag ? "none" : `transform ${ADVANCE_MS}ms cubic-bezier(.2,.8,.2,1), opacity 320ms var(--ease)`;

  return (
    <figure className="m-0 grid gap-2" aria-label={`Photographs from the reports, ${n} of them`}>
      <div
        tabIndex={0}
        role="group"
        aria-roledescription="photo deck"
        aria-label={`Photo ${i + 1} of ${n}: ${cur.source_name}`}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") { e.preventDefault(); go(1); }
          if (e.key === "ArrowLeft") { e.preventDefault(); go(-1); }
        }}
        className="relative aspect-[16/9] rounded-[var(--r-record)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{ marginRight: n > 1 ? 30 : 0, touchAction: "pan-y" }}
      >
        {live.map((p, j) => {
          const d = (j - i + n) % n;
          const isLeaving = leaving?.key === p.key && j !== i;
          let transform: string;
          let opacity: number;
          let z: number;
          if (isLeaving) {
            transform = `translateX(${leaving!.dir > 0 ? -70 : 70}%) rotate(${leaving!.dir > 0 ? -5 : 5}deg)`;
            opacity = 0;
            z = 5;
          } else if (d < PEEK.length) {
            const k = PEEK[d];
            transform = d === 0 && drag ? `translateX(${drag.dx}px) rotate(${drag.dx / PX_PER_DEGREE}deg)` : `translateX(${k.x}px) scale(${k.s})`;
            opacity = k.o;
            z = 4 - d;
          } else {
            transform = "translateX(30px) scale(.88)";
            opacity = 0;
            z = 0;
          }
          const front = d === 0;
          return (
            <div
              key={p.key}
              aria-hidden={!front}
              onPointerDown={front ? onDown : undefined}
              onPointerMove={front ? onMove : undefined}
              onPointerUp={front ? onUp : undefined}
              onPointerCancel={front ? onUp : undefined}
              className="absolute inset-0 select-none"
              style={{
                zIndex: z,
                transform,
                transformOrigin: "right center",
                opacity,
                transition,
                boxShadow: front ? "var(--shadow-1)" : "none",
                outline: front ? "none" : "1px solid var(--line)",
                borderRadius: "var(--r-record)",
                cursor: front && n > 1 ? (drag ? "grabbing" : "grab") : "default",
              }}
            >
              {/* The photo is dragged, not followed: the report opens from "Their report" below. */}
              <div className="p-thumb absolute inset-0" onErrorCapture={() => setDead((s) => new Set(s).add(p.key))} draggable={false}>
                <PhotoImg src={p.image_url} alt={`Photo: ${p.source_name}`} eager={j === 0} className="pointer-events-none" />
                <span className="p-thumb__credit">
                  <OutletIcon domain={p.domain} code={p.code ?? fallbackCode(p.source_name)} name={p.source_name} size={16} />
                  {p.source_name}
                </span>
              </div>
            </div>
          );
        })}
        {n > 1 && (
          <>
            <button type="button" className="p-iconbtn absolute left-2 top-1/2 z-[6] -translate-y-1/2" aria-label="Previous photo" onClick={() => go(-1)} style={{ background: "color-mix(in srgb, var(--paper) 88%, transparent)" }}>
              <ArrowLeft />
            </button>
            <button type="button" className="p-iconbtn absolute right-2 top-1/2 z-[6] -translate-y-1/2" aria-label="Next photo" onClick={() => go(1)} style={{ background: "color-mix(in srgb, var(--paper) 88%, transparent)" }}>
              <ArrowRight />
            </button>
            <span className="p-mono absolute right-2.5 top-2.5 z-[6] rounded-[2px] px-1.5 py-[3px] text-[11px]" aria-live="polite" style={{ background: "color-mix(in srgb, var(--paper) 88%, transparent)", color: "var(--ink)" }}>
              {i + 1} / {n}
            </span>
          </>
        )}
      </div>
      <figcaption className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[12.5px] leading-[1.35]" style={{ color: "var(--ink-3)" }}>
        <span className="min-w-0">Photo: <b className="font-semibold" style={{ color: "var(--ink-2)" }}>{cur.source_name}</b> — a preview of their report</span>
        <a href={cur.url} target="_blank" rel="noopener noreferrer" className="ml-auto inline-flex min-h-[44px] items-center font-semibold lg:min-h-[32px]" style={{ color: "var(--accent)" }}>
          Their report ↗
        </a>
      </figcaption>
      {n > 1 && (
        <div className="p-hide-scroll -m-1 flex gap-1.5 overflow-x-auto p-1">
          {live.map((p, j) => (
            <button
              key={p.key}
              type="button"
              onClick={() => show(j, j > i ? 1 : -1)}
              aria-label={`Photo ${j + 1}: ${p.source_name}`}
              aria-current={j === i ? "true" : undefined}
              className="relative h-11 w-16 shrink-0 overflow-hidden lg:h-[38px] lg:w-[56px] rounded-[2px] transition-[outline-color] duration-150"
              style={{ background: "var(--sunken)", outline: j === i ? "2px solid var(--ink)" : "1px solid var(--line)", outlineOffset: j === i ? 1 : 0 }}
            >
              <PhotoImg src={p.image_url} alt="" />
            </button>
          ))}
        </div>
      )}
    </figure>
  );
}
