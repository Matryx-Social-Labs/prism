// The chart's stroke icons: one set, currentColor, 2px stroke, the bottom
// bar's grammar. Text glyphs (↗ ▲ ▼ ↳ ▾) render in whatever face the fallback
// stack finds and read as costume; these read as the same ink at every size.
type P = { size?: number; className?: string };
const base = (size: number) => ({
  width: size, height: size, viewBox: "0 0 24 24", fill: "none", stroke: "currentColor",
  strokeWidth: 2, strokeLinecap: "round" as const, strokeLinejoin: "round" as const, "aria-hidden": true,
});

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
