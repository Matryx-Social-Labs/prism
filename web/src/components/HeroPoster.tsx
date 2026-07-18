// The hero figure: one story refracted into many perspectives.
// Animated, label-free, drawn on the page background in the page's own
// theme — no lens is named (the lens set grows over time). Also serves as
// the reduced-motion / no-WebGL / light-theme visual, so those users never
// download the three.js chunk.

const RAYS = [
  { x2: 560, y2: 12, color: "#f59e0b", delay: "0s" },
  { x2: 562, y2: 48, color: "#ef4444", delay: "0.12s" },
  { x2: 564, y2: 80, color: "#10b981", delay: "0.24s" },
  { x2: 562, y2: 112, color: "#06b6d4", delay: "0.36s" },
  { x2: 560, y2: 148, color: "#8b5cf6", delay: "0.48s" },
];

export function HeroPoster() {
  return (
    <div className="mx-auto w-full max-w-[520px] xl:max-w-[560px]" aria-hidden>
      <svg viewBox="0 0 620 160" className="w-full" role="img" aria-label="One story refracted into many perspectives">
        <defs>
          <linearGradient id="hero-beam-in" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.9" />
          </linearGradient>
        </defs>
        <line className="beam-in" x1="10" y1="80" x2="255" y2="80" stroke="url(#hero-beam-in)" strokeWidth="2.5" />
        <path
          className="prism-glow"
          d="M288 42 L324 118 L252 118 Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        {RAYS.map((r) => (
          <line
            key={r.color}
            className="beam-out"
            x1="318"
            y1="80"
            x2={r.x2}
            y2={r.y2}
            stroke={r.color}
            strokeWidth="2.4"
            opacity="0.9"
            style={{ animationDelay: r.delay }}
          />
        ))}
        <text x="10" y="66" fontSize="11" fill="var(--ink-faint)" fontFamily="inherit">
          one story
        </text>
        <text x="486" y="158" fontSize="11" fill="var(--ink-faint)" fontFamily="inherit">
          every perspective
        </text>
      </svg>
    </div>
  );
}
