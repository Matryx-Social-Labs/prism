"use client";

import { useEffect, useRef, useState } from "react";
import { OutletIcon } from "@/components/Coverage";
import { REPORT_IMAGES } from "@/lib/images";
import type { StoryPhoto } from "@/lib/api";

// A story is many reports, so its picture is many pictures: up to three of
// them as a small pile on the row, the newest in front, each the outlet's own
// and credited (the front photo carries the icon; every alt names its outlet).
// Motion, two beats and no loop (DESIGN.md § Motion): the pile SETTLES when
// the row comes into view — the cards behind slide out from under the front
// one into their fan, 480ms on a spring, staggered — and on a desk a hover
// spreads it a little further so the pictures behind show. Each photo fades
// in as it loads. Reduced motion places everything at once. A "+N" counts the
// rest. The whole row is the link; the pile is not a second one.
export function PhotoStack({ photos, size = "row" }: { photos: StoryPhoto[]; size?: "row" | "lead" }) {
  const ref = useRef<HTMLElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { setInView(true); io.disconnect(); } }, { rootMargin: "0px 0px -10% 0px" });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  if (!REPORT_IMAGES || photos.length === 0) return null;
  const shown = photos.slice(0, 3);
  const rest = photos.length - shown.length;
  const w = size === "lead" ? 180 : 96;
  const h = size === "lead" ? 128 : 70;
  return (
    <figure ref={ref} className={`photo-stack relative shrink-0 ${inView ? "is-in" : ""}`} style={{ width: w + 18, height: h + 12 }} aria-label={`${photos.length} ${photos.length === 1 ? "photograph" : "photographs"} from the reports`}>
      {shown.map((p, i) => {
        // Front = index 0; the others peek out behind, up and to the right.
        const depth = shown.length - 1 - i;
        return (
          <span
            key={p.url}
            className="photo-stack__card absolute overflow-hidden rounded-[8px] border"
            style={{
              width: w,
              height: h,
              left: 0,
              bottom: 0,
              zIndex: 10 - depth,
              // The fan, as variables the stylesheet animates to.
              ["--fan-x" as string]: `${depth * 9}px`,
              ["--fan-y" as string]: `${-depth * 5}px`,
              ["--fan-r" as string]: `${depth === 0 ? 0 : depth === 1 ? -4 : 4}deg`,
              transitionDelay: `${depth * 70}ms`,
              borderColor: "var(--surface)",
              boxShadow: "var(--shadow-1)",
              background: "var(--sunken)",
            }}
          >
            <Photo src={p.url} alt={p.outlet ? `Photo: ${p.outlet.name}` : "Photo from a report"} />
            {depth === 0 && p.outlet && (
              <span className="absolute bottom-1 left-1 rounded-full" style={{ boxShadow: "0 0 0 1.5px var(--surface)" }} title={`Photo: ${p.outlet.name}`}>
                <OutletIcon domain={p.outlet.domain} code={p.outlet.code} name={p.outlet.name} size={18} />
              </span>
            )}
            {depth === 0 && rest > 0 && (
              <span className="absolute bottom-1 right-1 rounded-full px-1.5 py-0.5 font-mono text-[10.5px] tabular-nums text-white" style={{ background: "rgba(0,0,0,.6)" }} aria-hidden>+{rest}</span>
            )}
          </span>
        );
      })}
    </figure>
  );
}

/** A photograph that fades in when its bytes land, instead of popping. */
function Photo({ src, alt }: { src: string; alt: string }) {
  const [ready, setReady] = useState(false);
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={src} alt={alt} loading="lazy" decoding="async" referrerPolicy="no-referrer" onLoad={() => setReady(true)} className={`photo-fade h-full w-full object-cover ${ready ? "is-ready" : ""}`} />
  );
}
