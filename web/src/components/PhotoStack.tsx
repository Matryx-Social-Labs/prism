"use client";

import { useEffect, useRef, useState } from "react";
import { OutletIcon } from "@/components/Coverage";
import { PhotoImg } from "@/components/PhotoImg";
import { REPORT_IMAGES } from "@/lib/images";
import type { StoryPhoto } from "@/lib/api";

// Design System v2 · PhotoPile (media/PhotoDeck.jsx; guidelines/motion.html
// "Pile · fan-in"): a story is many reports, so its picture is up to three of
// their photographs, each the outlet's own and credited (the front one carries
// the outlet's icon; every alt names its outlet). The cards start squared under
// the front one and settle into a fan ONCE, when the row is 40% in view — 480ms
// on a spring, 60ms stagger — and a hover on the row spreads the fan ×1.9
// (globals.css .photo-stack). Each photo fades in over its sunken placeholder
// (PhotoImg). Reduced motion draws the pile already fanned. A "+N" counts the
// rest. The whole row is the link; the pile is not a second one.
const FAN = [
  { x: 0, y: 0, r: -4 },
  { x: 8, y: 3, r: 2 },
  { x: 16, y: 6, r: 6 },
];

export function PhotoStack({ photos }: { photos: StoryPhoto[] }) {
  const ref = useRef<HTMLElement>(null);
  const [inView, setInView] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    if (typeof IntersectionObserver === "undefined" || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setInView(true);
      return;
    }
    const io = new IntersectionObserver((es) => { if (es.some((e) => e.isIntersecting)) { setInView(true); io.disconnect(); } }, { threshold: 0.4 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  if (!REPORT_IMAGES || photos.length === 0) return null;
  const shown = photos.slice(0, 3);
  const rest = photos.length - shown.length;
  return (
    <figure
      ref={ref}
      className={`photo-stack relative shrink-0 ${inView ? "is-in" : ""}`}
      style={{ width: 124, height: 88 }}
      aria-label={`${photos.length} ${photos.length === 1 ? "photograph" : "photographs"} from the reports`}
    >
      {shown.map((p, i) => (
        <span
          key={p.url}
          className="p-thumb photo-stack__card"
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            width: 96,
            height: 68,
            zIndex: 3 - i,
            border: "2px solid var(--surface)",
            boxShadow: "var(--shadow-1)",
            ["--fan-x" as string]: `${FAN[i].x}px`,
            ["--fan-y" as string]: `${FAN[i].y}px`,
            ["--fan-r" as string]: `${FAN[i].r}deg`,
            transitionDelay: `${i * 60}ms`,
          }}
        >
          <PhotoImg src={p.url} alt={p.outlet ? `Photo: ${p.outlet.name}` : "Photo from a report"} />
          {i === 0 && p.outlet && (
            <span className="p-thumb__credit" title={`Photo: ${p.outlet.name}`}>
              <OutletIcon domain={p.outlet.domain} code={p.outlet.code} name={p.outlet.name} size={16} />
            </span>
          )}
          {i === 0 && rest > 0 && (
            <span className="p-thumb__credit p-mono" style={{ left: "auto", right: 4, padding: "2px 6px", fontSize: 10.5 }} aria-hidden>
              +{rest}
            </span>
          )}
        </span>
      ))}
    </figure>
  );
}
