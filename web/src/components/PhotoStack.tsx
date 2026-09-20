"use client";

import { OutletIcon } from "@/components/Coverage";
import { REPORT_IMAGES } from "@/lib/images";
import type { StoryPhoto } from "@/lib/api";

// A story is many reports, so its picture is many pictures: up to three of
// them fanned as a small pile on the row, the newest in front, each the
// outlet's own and credited (the front photo carries the icon; every alt
// names its outlet). Hover on a desk spreads the pile a few degrees so the
// ones behind show (160ms, no motion under reduced-motion). A "+N" counts
// the rest. The whole row is the link; the pile is not a second one.
export function PhotoStack({ photos, size = "row" }: { photos: StoryPhoto[]; size?: "row" | "lead" }) {
  if (!REPORT_IMAGES || photos.length === 0) return null;
  const shown = photos.slice(0, 3);
  const rest = photos.length - shown.length;
  const w = size === "lead" ? 180 : 112;
  const h = size === "lead" ? 128 : 80;
  return (
    <figure className="photo-stack relative shrink-0" style={{ width: w + 16, height: h + 12 }} aria-label={`${photos.length} ${photos.length === 1 ? "photograph" : "photographs"} from the reports`}>
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
              left: depth * 8,
              bottom: 0,
              zIndex: 10 - depth,
              transform: `rotate(${depth === 0 ? 0 : depth === 1 ? -3 : 3}deg) translateY(${-depth * 4}px)`,
              borderColor: "var(--surface)",
              boxShadow: "var(--shadow-1)",
              background: "var(--sunken)",
            }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={p.url} alt={p.outlet ? `Photo: ${p.outlet.name}` : "Photo from a report"} loading="lazy" decoding="async" referrerPolicy="no-referrer" className="h-full w-full object-cover" />
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
