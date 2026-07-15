// Static hero figure: the beam→prism→spectrum story in pure SVG/CSS.
// Serves as the loading state and the reduced-motion / no-WebGL fallback
// for the 3D prism, so those users never download the three.js chunk.
export function HeroPoster() {
  return (
    <div className="mx-auto mt-10 max-w-xl" aria-hidden>
      <svg viewBox="0 0 560 150" className="w-full">
        <defs>
          <linearGradient id="beamW" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="currentColor" stopOpacity="0" />
            <stop offset="100%" stopColor="currentColor" stopOpacity="0.9" />
          </linearGradient>
        </defs>
        <line x1="10" y1="75" x2="225" y2="75" stroke="url(#beamW)" strokeWidth="2.5" className="beam-in" />
        <path
          d="M258 40 L292 110 L224 110 Z"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinejoin="round"
          className="prism-glow"
        />
        <line x1="290" y1="80" x2="550" y2="28" stroke="#f59e0b" strokeWidth="2.5" className="beam-out" opacity="0.9" />
        <line x1="290" y1="86" x2="550" y2="86" stroke="#06b6d4" strokeWidth="2.5" className="beam-out" opacity="0.9" />
        <line x1="290" y1="92" x2="550" y2="140" stroke="#8b5cf6" strokeWidth="2.5" className="beam-out" opacity="0.9" />
      </svg>
    </div>
  );
}
