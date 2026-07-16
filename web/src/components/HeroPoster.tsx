// Static hero figure: one beam of news refracted into three labeled lenses.
// Serves as the loading state and the reduced-motion / no-WebGL fallback
// for the 3D prism, so those users never download the three.js chunk.
export function HeroPoster() {
  return (
    <div className="flex justify-center" aria-hidden>
      <svg
        viewBox="0 0 360 260"
        className="w-full max-w-[420px]"
        aria-label="A beam of news split into three lenses"
      >
        <line className="beam-in" x1="0" y1="130" x2="150" y2="130" stroke="var(--ink)" strokeWidth="2" />
        <path
          className="prism-glow"
          d="M180 55 L235 175 L125 175 Z"
          fill="none"
          stroke="var(--ink)"
          strokeWidth="2"
          strokeLinejoin="round"
        />
        <line className="beam-out" x1="205" y1="120" x2="345" y2="62" stroke="var(--lens-general)" strokeWidth="2.4" />
        <line className="beam-out" x1="210" y1="138" x2="350" y2="138" stroke="var(--lens-cyber)" strokeWidth="2.4" />
        <line className="beam-out" x1="205" y1="156" x2="345" y2="214" stroke="var(--lens-finance)" strokeWidth="2.4" />
        <text x="300" y="50" fontSize="12" fontWeight="600" fill="var(--lens-general)" fontFamily="inherit">
          Reader
        </text>
        <text x="308" y="128" fontSize="12" fontWeight="600" fill="var(--lens-cyber)" fontFamily="inherit">
          Cyber
        </text>
        <text x="296" y="236" fontSize="12" fontWeight="600" fill="var(--lens-finance)" fontFamily="inherit">
          Markets
        </text>
        <text x="8" y="118" fontSize="11" fill="var(--ink-faint)" fontFamily="inherit">
          one event
        </text>
      </svg>
    </div>
  );
}
