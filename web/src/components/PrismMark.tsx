// The brand glyph: a prism outline with the spectrum beam falling through it.
export function PrismMark({ size = 22 }: { size?: number }) {
  return (
    <svg width={size} height={(size * 20) / 22} viewBox="0 0 24 22" aria-hidden="true">
      <path
        d="M12 1 L23 21 L1 21 Z"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinejoin="round"
      />
      <path d="M12 8 L12 21" stroke="url(#prism-mark-g)" strokeWidth="1.6" />
      <defs>
        <linearGradient id="prism-mark-g" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#f59e0b" />
          <stop offset="50%" stopColor="#06b6d4" />
          <stop offset="100%" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
    </svg>
  );
}
