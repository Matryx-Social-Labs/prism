"use client";

import { useId } from "react";

// The brand glyph: the prism (Prism Landing Desktop.dc.html / Prism Desktop.dc.html).
//
// A solid triangle standing on a spectrum bar — white light enters, the spectrum
// leaves. It is the product's pitch as a shape, and it is why the design system
// carries a spectrum hairline and discrete lens hues at all.
//
// The triangle inherits `currentColor`, so it is ink on ivory and ivory on
// charcoal. The base bar is the one colored element, and it is legal under
// DESIGN.md's spectrum rule — "hairline bars (2–3px)" — because 3 units of a
// 22-unit viewBox renders at ~2.6px at header size. It is not a colored chrome
// element; it is the brand accent doing the single job it is sanctioned for.
export function PrismMark({ size = 21 }: { size?: number }) {
  // The design defines the gradient once per page and lets later marks reference
  // it by a shared id. That works in a static document and breaks here: two marks
  // on one page (header + footer) would emit duplicate ids, and if React unmounts
  // the first the second loses its paint and the bar renders empty. Scope it per
  // instance instead. useId embeds colons, which are legal in an id and in url()
  // but not in a querySelector, so strip them rather than leave a footgun.
  const gid = `prism-spectrum-${useId().replace(/:/g, "")}`;
  return (
    <svg
      width={size}
      // 24:22 is the mark's own ratio — deriving the height keeps it from
      // stretching at the four sizes the design uses (14, 18, 21, 22).
      height={Math.round((size * 22) / 24)}
      viewBox="0 0 24 22"
      fill="none"
      aria-hidden="true"
      style={{ flex: "none" }}
    >
      <path
        d="M12 1 L23 21 L1 21 Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth={1.5}
        strokeLinejoin="round"
      />
      <rect x="1" y="19" width="22" height="3" fill={`url(#${gid})`} />
      <defs>
        <linearGradient id={gid} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#ef4444" />
          <stop offset="35%" stopColor="#f59e0b" />
          <stop offset="70%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
    </svg>
  );
}
