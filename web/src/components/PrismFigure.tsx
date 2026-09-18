/**
 * The brand figure, drawn as the physics happens (design/board/build.py has the
 * same construction): ONE beam of white light enters the left face of an
 * equilateral prism rising slightly, bends toward the base on entry and again
 * on exit, and leaves as a fan — red least deviated, violet most. Snell's law
 * with an exaggerated dispersion (n 1.44 → 1.58) so the fan reads at 400px.
 * One story in; every perspective out. A prism separates — it never combines —
 * so the figure does not pretend many reports flow into it.
 */
type V = [number, number];
const unit = ([x, y]: V): V => {
  const l = Math.hypot(x, y);
  return [x / l, y / l];
};
/** Vector Snell. `n` points against the incoming ray. null on total internal reflection. */
function refract(d: V, n: V, eta: number): V | null {
  const ci = -(d[0] * n[0] + d[1] * n[1]);
  const k = 1 - eta * eta * (1 - ci * ci);
  if (k < 0) return null;
  const f = eta * ci - Math.sqrt(k);
  return unit([eta * d[0] + f * n[0], eta * d[1] + f * n[1]]);
}
function hit(p: V, d: V, a: V, b: V): V | null {
  const s: V = [b[0] - a[0], b[1] - a[1]];
  const den = d[0] * s[1] - d[1] * s[0];
  if (Math.abs(den) < 1e-9) return null;
  const qp: V = [a[0] - p[0], a[1] - p[1]];
  const t = (qp[0] * s[1] - qp[1] * s[0]) / den;
  const u = (qp[0] * d[1] - qp[1] * d[0]) / den;
  return t > 0 && u >= 0 && u <= 1 ? [p[0] + t * d[0], p[1] + t * d[1]] : null;
}

const APEX: V = [170, 61.4];
const BL: V = [90, 200];
const BR: V = [250, 200];
const N_LEFT = unit([-138.6, -80]); // outward normal, left face
const N_RIGHT_IN = unit([-138.6, 80]); // inward normal, right face (against the exiting ray)
const STOPS: [string, number][] = [["#ef4444", 1.44], ["#f59e0b", 1.47], ["#06b6d4", 1.52], ["#8b5cf6", 1.58]];

export function PrismFigure({ className = "" }: { className?: string }) {
  const ang = (-10 * Math.PI) / 180; // the beam rises slightly into the prism
  const d0: V = [Math.cos(ang), Math.sin(ang)];
  const m1: V = [(APEX[0] + BL[0]) / 2 + 6, (APEX[1] + BL[1]) / 2 + 10];
  const start: V = [m1[0] - 118 * d0[0], m1[1] - 118 * d0[1]];
  const rays = STOPS.map(([c, n]) => {
    const t1 = refract(d0, N_LEFT, 1 / n);
    if (!t1) return null;
    const h = hit(m1, t1, APEX, BR);
    const t2 = h && refract(t1, N_RIGHT_IN, n);
    if (!h || !t2) return null;
    return { c, h, end: [h[0] + 135 * t2[0], h[1] + 135 * t2[1]] as V };
  }).filter((r): r is { c: string; h: V; end: V } => r !== null);
  const f = (n: number) => n.toFixed(1);
  return (
    <svg className={className} viewBox="0 0 400 260" role="img" aria-label="One beam of white light enters a prism and leaves as a spectrum: one story in, every perspective out">
      <defs>
        <linearGradient id="prism-fig-base" x1="0" x2="1">
          <stop offset="0" stopColor="#ef4444" /><stop offset=".35" stopColor="#f59e0b" /><stop offset=".7" stopColor="#06b6d4" /><stop offset="1" stopColor="#8b5cf6" />
        </linearGradient>
      </defs>
      <path d={`M${APEX[0]} ${APEX[1]} L${BR[0]} ${BR[1]} L${BL[0]} ${BL[1]} Z`} fill="var(--surface)" stroke="var(--ink)" strokeWidth="2" strokeLinejoin="round" />
      <rect x={BL[0]} y={BL[1] - 4} width={BR[0] - BL[0]} height="5" fill="url(#prism-fig-base)" />
      <line x1={f(start[0])} y1={f(start[1])} x2={f(m1[0])} y2={f(m1[1])} stroke="var(--ink)" strokeWidth="3" strokeLinecap="round" />
      {rays.map((r) => (
        <line key={`in-${r.c}`} x1={f(m1[0])} y1={f(m1[1])} x2={f(r.h[0])} y2={f(r.h[1])} stroke={r.c} strokeWidth="2" strokeOpacity=".7" />
      ))}
      {rays.map((r) => (
        <line key={`out-${r.c}`} x1={f(r.h[0])} y1={f(r.h[1])} x2={f(r.end[0])} y2={f(r.end[1])} stroke={r.c} strokeWidth="3" strokeLinecap="round" />
      ))}
      <text x={Math.round(start[0])} y={Math.round(start[1] - 12)} fontFamily="var(--font-ui)" fontSize="10.5" fontWeight="600" fill="var(--ink-3)" letterSpacing="1">ONE STORY</text>
      <text x="398" y="254" textAnchor="end" fontFamily="var(--font-ui)" fontSize="10.5" fontWeight="600" fill="var(--ink-3)" letterSpacing="1">EVERY PERSPECTIVE</text>
    </svg>
  );
}
