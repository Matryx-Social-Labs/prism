// The brand glyph (matches the design mockup): a solid prism triangle with the
// spectrum beam refracted along its base.
export function PrismMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={(size * 20) / 22} viewBox="0 0 24 22" aria-hidden="true">
      <path
        d="M12 1 L23 21 L1 21 Z"
        fill="currentColor"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <rect x="1" y="19" width="22" height="3" fill="url(#prism-mark-g)" />
      <defs>
        <linearGradient id="prism-mark-g" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="#ef4444" />
          <stop offset="35%" stopColor="#f59e0b" />
          <stop offset="70%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
    </svg>
  );
}
