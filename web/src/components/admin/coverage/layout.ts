// Where each outlet sits in the 3D coverage network: a spring-electric layout
// (Fruchterman–Reingold) in three dimensions. Every pair of outlets pushes
// apart; a link pulls its two outlets together, harder the more stories they
// share. Started from fixed points on a sphere, never from random ones, so the
// same data always draws the same picture — a founder comparing two weeks is
// comparing the data, not two dice rolls.
//
// ponytail: O(n²) per step. ~50 outlets today, fine to a few hundred; switch to
// a Barnes–Hut octree (d3-force-3d) if outlets reach the thousands.

export type Point3 = [number, number, number];

export interface Link {
  a: string;
  b: string;
  shared: number;
}

const STEPS = 300;
export const RADIUS = 10;
/** No outlet is drawn further out than this: one with few links sits on the
 *  rim, in view, rather than wherever the push left it. */
export const RIM = 1.3 * RADIUS;
/** A pull to the centre (Gephi's Fruchterman–Reingold gravity), so parts of
 *  the network with no link between them stay near each other. */
const GRAVITY = 0.1;

/** n points spread evenly over a sphere (the Fibonacci lattice). */
function sphere(n: number): Point3[] {
  const golden = Math.PI * (3 - Math.sqrt(5));
  return Array.from({ length: n }, (_, i) => {
    const y = n === 1 ? 0 : 1 - (i / (n - 1)) * 2;
    const r = Math.sqrt(1 - y * y);
    return [Math.cos(golden * i) * r, y, Math.sin(golden * i) * r];
  });
}

export function layout(ids: string[], links: Link[], steps = STEPS): Map<string, Point3> {
  const n = ids.length;
  const at = sphere(n).map((p) => p.map((v) => v * RADIUS) as Point3);
  const index = new Map(ids.map((id, i) => [id, i]));
  const most = Math.max(1, ...links.map((l) => l.shared));
  const edges = links
    .filter((l) => index.has(l.a) && index.has(l.b))
    .map((l) => ({ i: index.get(l.a)!, j: index.get(l.b)!, w: Math.log1p(l.shared) / Math.log1p(most) }));
  const k = (2 * RADIUS) / Math.cbrt(Math.max(1, n));
  for (let step = 0; step < steps; step++) {
    const heat = (RADIUS / 5) * (1 - step / steps);
    const move: Point3[] = at.map(() => [0, 0, 0]);
    for (let i = 0; i < n; i++) {
      for (let j = i + 1; j < n; j++) {
        const d = at[i].map((v, c) => v - at[j][c]);
        const dist = Math.max(0.01, Math.hypot(...d));
        const push = (k * k) / dist;
        for (let c = 0; c < 3; c++) {
          move[i][c] += (d[c] / dist) * push;
          move[j][c] -= (d[c] / dist) * push;
        }
      }
    }
    for (const { i, j, w } of edges) {
      const d = at[i].map((v, c) => v - at[j][c]);
      const dist = Math.max(0.01, Math.hypot(...d));
      const pull = ((dist * dist) / k) * w;
      for (let c = 0; c < 3; c++) {
        move[i][c] -= (d[c] / dist) * pull;
        move[j][c] += (d[c] / dist) * pull;
      }
    }
    for (let i = 0; i < n; i++) {
      for (let c = 0; c < 3; c++) move[i][c] -= GRAVITY * k * at[i][c];
      const len = Math.max(0.01, Math.hypot(...move[i]));
      const by = Math.min(len, heat);
      at[i] = at[i].map((v, c) => v + (move[i][c] / len) * by) as Point3;
    }
  }
  const fitted = fit(at);
  return new Map(ids.map((id, i) => [id, fitted[i]]));
}

/** Centred, scaled so most outlets fill a sphere of RADIUS, the rest pulled in
 *  to the rim — the camera frames RADIUS, so everything is in view. */
function fit(at: Point3[]): Point3[] {
  if (at.length === 0) return at;
  const centre = [0, 1, 2].map((c) => at.reduce((a, p) => a + p[c], 0) / at.length);
  const moved = at.map((p) => p.map((v, c) => v - centre[c]) as Point3);
  const radii = moved.map((p) => Math.hypot(...p)).sort((a, b) => a - b);
  const scale = RADIUS / Math.max(0.01, radii[Math.floor(0.9 * (radii.length - 1))]);
  return moved.map((p) => {
    const r = Math.hypot(...p) * scale;
    const f = r > RIM ? (RIM / r) * scale : scale;
    return p.map((v) => v * f) as Point3;
  });
}
