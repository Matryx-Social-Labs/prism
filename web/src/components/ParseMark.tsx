// The brand glyph: "the bracketed record" (Parse Identity.dc.html, winner).
//
// A citation bracket pair holding three rules — one file, read three ways, the
// last rule short because the record is still open. It borrows the product's own
// provenance glyph: `[3]` is how every grounded answer cites its sources. A
// bracket contains without concluding, which is the whole positioning.
//
// MONOCHROME by contract. It inherits `currentColor`, so it is ink on ivory and
// ivory on charcoal. The 3px spectrum bar is the brand's only colored object —
// a permanently colored mark would break the rule that color means a lens is
// speaking. The one sanctioned exception is `lens` below.
export function ParseMark({
  size = 21,
  lens,
}: {
  size?: number;
  // Story pages only: the mark re-inks with the flip so the masthead itself
  // states which lens is speaking. Legal precisely because it means a lens IS
  // speaking. Never set this on the landing, the feed, or marketing surfaces —
  // the exception only holds if it stays rare.
  lens?: string;
}) {
  // Optical compensation: the bracket needs more weight as it shrinks or the
  // interior rules close up. Values taken from the identity sheet.
  const stroke = size <= 16 ? 2.1 : size <= 22 ? 1.9 : size <= 40 ? 1.7 : 1.6;
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke={lens ?? "currentColor"}
      strokeWidth={stroke}
      strokeLinecap="square"
      aria-hidden="true"
      style={lens ? { transition: "stroke 500ms ease-out" } : undefined}
    >
      <path d="M8.5 3.5H4.5v17h4" />
      <path d="M15.5 3.5h4v17h-4" />
      <path d="M9.6 8.5h4.8" />
      <path d="M9.6 12h4.8" />
      <path d="M9.6 15.5h2.9" />
    </svg>
  );
}
