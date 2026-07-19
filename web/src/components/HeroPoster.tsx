// The hero figure: one story refracted into many perspectives.
// Animated, label-free, drawn on the page background in the page's own
// theme — no lens is named (the lens set grows over time). Also serves as
// the reduced-motion / no-WebGL / light-theme visual, so those users never
// download the three.js chunk. A glassy filled prism with a soft glow reads
// as premium even without WebGL, rather than a hollow CAD outline.

const RAYS = [
  { x2: 566, y2: 20, color: "#f59e0b", delay: "0s" },
  { x2: 570, y2: 52, color: "#ef4444", delay: "0.1s" },
  { x2: 572, y2: 80, color: "#10b981", delay: "0.2s" },
  { x2: 570, y2: 108, color: "#06b6d4", delay: "0.3s" },
  { x2: 566, y2: 140, color: "#8b5cf6", delay: "0.4s" },
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
          {/* glass body: a cool, near-neutral vertical sheen — monochrome chrome,
              the spectrum lives only in the rays (DESIGN.md color rule) */}
          <linearGradient id="hero-prism-glass" x1="0" y1="0" x2="0.4" y2="1">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0.14" />
            <stop offset="55%" stopColor="currentColor" stopOpacity="0.05" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.1" />
          </linearGradient>
          {/* per-ray fade so the spectrum dissolves into the page, not hard lines */}
          {RAYS.map((r, i) => (
            <linearGradient key={r.color} id={`hero-ray-${i}`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={r.color} stopOpacity="0.95" />
              <stop offset="100%" stopColor={r.color} stopOpacity="0.15" />
            </linearGradient>
          ))}
          <filter id="hero-soft-glow" x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="2.2" result="b" />
            <feMerge>
              <feMergeNode in="b" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* incoming beam */}
        <line className="beam-in" x1="10" y1="80" x2="256" y2="80" stroke="url(#hero-beam-in)" strokeWidth="2.5" />

        {/* the prism: filled glass body + a bright leading edge, softly glowing */}
        <g filter="url(#hero-soft-glow)">
          <path
            d="M288 40 L326 120 L250 120 Z"
            fill="url(#hero-prism-glass)"
            stroke="currentColor"
            strokeOpacity="0.35"
            strokeWidth="1.5"
            strokeLinejoin="round"
          />
          {/* leading facet the beam strikes — the brightest line */}
          <line
            className="prism-glow"
            x1="288"
            y1="40"
            x2="250"
            y2="120"
            stroke="currentColor"
            strokeOpacity="0.7"
            strokeWidth="1.75"
            strokeLinecap="round"
          />
        </g>

        {/* refracted spectrum */}
        <g filter="url(#hero-soft-glow)">
          {RAYS.map((r, i) => (
            <line
              key={r.color}
              className="beam-out"
              x1="315"
              y1="80"
              x2={r.x2}
              y2={r.y2}
              stroke={`url(#hero-ray-${i})`}
              strokeWidth="2.4"
              strokeLinecap="round"
              style={{ animationDelay: r.delay }}
            />
          ))}
        </g>

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
