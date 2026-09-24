// The stroke icons: one set, currentColor, the only icon family (DESIGN.md).
// Text glyphs (↗ ▲ ▼ ↳ ▾) render in whatever face the fallback stack finds and
// read as costume; these read as the same ink at every size. Navigation icons
// are 22px at a 1.8 stroke; inline glyphs keep 2px.
type P = { size?: number; className?: string };
const base = (size: number, sw = 2) => ({
  width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: sw, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true,
});

export const TodayIcon = ({ size = 22, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><rect x="3" y="4" width="18" height="17" rx="3" /><path d="M3 9h18M8 2v4M16 2v4" /></svg>
);
export const StoriesIcon = ({ size = 22, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><path d="M4 19V5M4 12h7M4 5h11M11 12l4-3M15 5l5 3" /><circle cx="20" cy="8" r="1.5" fill="currentColor" stroke="none" /><circle cx="15" cy="9" r="1.5" fill="currentColor" stroke="none" /></svg>
);
export const SearchIcon = ({ size = 22, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></svg>
);
export const WatchlistIcon = ({ size = 22, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><path d="M4 16l5-5 4 4 7-8" /><path d="M15 7h5v5" /></svg>
);
export const YouIcon = ({ size = 22, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></svg>
);
export const BellIcon = ({ size = 18, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z" /><path d="M10 21a2 2 0 0 0 4 0" /></svg>
);
export const ShareIcon = ({ size = 18, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><path d="M12 15V4M7 9l5-5 5 5M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5" /></svg>
);
export const Check = ({ size = 13, className }: P) => (
  <svg {...base(size, 2.5)} className={className}><path d="m5 12 4 4L19 6" /></svg>
);
export const Lock = ({ size = 13, className }: P) => (
  <svg {...base(size)} className={className}><rect x="5" y="11" width="14" height="10" rx="2" /><path d="M8 11V8a4 4 0 0 1 8 0v3" /></svg>
);
export const ArrowRight = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}><path d="M5 12h14M13 6l6 6-6 6" /></svg>
);
export const ArrowLeft = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}><path d="M19 12H5M11 6l-6 6 6 6" /></svg>
);
export const SunIcon = ({ size = 18, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><circle cx="12" cy="12" r="4" /><path d="M12 2v2M12 20v2M2 12h2M20 12h2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4" /></svg>
);
export const MoonIcon = ({ size = 18, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z" /></svg>
);

export const ArrowUpRight = ({ size = 14, className }: P) => (
  <svg {...base(size)} className={className}><path d="M7 17L17 7M9 7h8v8" /></svg>
);
export const ArrowUp = ({ size = 12, className }: P) => (
  <svg {...base(size)} className={className}><path d="M12 19V5M5 12l7-7 7 7" /></svg>
);
export const ArrowDown = ({ size = 12, className }: P) => (
  <svg {...base(size)} className={className}><path d="M12 5v14M5 12l7 7 7-7" /></svg>
);
export const Dash = ({ size = 12, className }: P) => (
  <svg {...base(size)} className={className}><path d="M5 12h14" /></svg>
);
/** A branch leaving the trunk: down, then right. */
export const Corner = ({ size = 12, className }: P) => (
  <svg {...base(size)} className={className}><path d="M6 4v9a3 3 0 0 0 3 3h9M14 12l4 4-4 4" /></svg>
);
export const ChevronDown = ({ size = 12, className }: P) => (
  <svg {...base(size)} className={className}><path d="M6 9l6 6 6-6" /></svg>
);
export const Speech = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}><path d="M4 5h16v11H9l-5 4z" /></svg>
);
export const Close = ({ size = 14, className }: P) => (
  <svg {...base(size)} className={className}><path d="M6 6l12 12M18 6L6 18" /></svg>
);
export const Play = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className} fill="currentColor" stroke="none"><path d="M7 4.5v15l12-7.5z" /></svg>
);
export const Pause = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className} fill="currentColor" stroke="none"><path d="M6 4h4v16H6zM14 4h4v16h-4z" /></svg>
);
export const SkipNext = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className} fill="currentColor" stroke="none"><path d="M5 5v14l9-7zM16 5h3v14h-3z" /></svg>
);
// The X mark, drawn in the set's own stroke: the display rules ask for the
// logo on every post shown off-platform; the design asks for one icon family.
export const XIcon = ({ size = 14, className }: P) => (
  <svg {...base(size)} className={className}><path d="M4 4l16 16M20 4L4 20" /></svg>
);
export const Headphones = ({ size = 16, className }: P) => (
  <svg {...base(size)} className={className}><path d="M4 14v-2a8 8 0 0 1 16 0v2" /><path d="M4 14h3v6H5a1 1 0 0 1-1-1zM20 14h-3v6h2a1 1 0 0 0 1-1z" /></svg>
);
/** "Where this number comes from" — the admin charts' provenance tip. */
export const InfoIcon = ({ size = 16, className }: P) => (
  <svg {...base(size, 1.8)} className={className}><circle cx="12" cy="12" r="9" /><path d="M12 11v5" /><circle cx="12" cy="7.8" r="1" fill="currentColor" stroke="none" /></svg>
);
