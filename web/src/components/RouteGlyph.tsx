import type { RouteData } from "@/lib/api";
import { routeShape } from "@/lib/route";

/**
 * The shape of a story in one line, for the chart of arcs: the main line's
 * stations, a branch as a stub above (its length in stations), a satellite as
 * a dotted stub below, the latest station filled. Read with the same
 * routeShape as the route page, so the glyph is the map in miniature and
 * never disagrees with it. Decorative: the counts beside it are the words.
 */
export function RouteGlyph({ route, className = "" }: { route: RouteData | null; className?: string }) {
  if (!route || route.nodes.length === 0) return null;
  const devs = route.nodes.map((n) => ({ id: n.id, title: "", sector: null, occurred_at: n.occurred_at, image_url: null, is_current: false, why: null }));
  const tree = { root_id: route.root_id, nodes: route.nodes.map((n) => ({ id: n.id, parent_id: n.parent_id, off_spine: n.off_spine, depth: 0 })), shape: { developments: devs.length, branches: 0, satellites: 0, max_depth: 0 } };
  const shape = routeShape(tree, devs);
  if (shape.trunk.length === 0) return null;
  const W = 260, n = shape.trunk.length, step = n > 1 ? Math.min(40, (W - 20) / (n - 1)) : 0;
  const xs = shape.trunk.map((_, i) => 10 + i * step);
  const at = (id: string) => xs[Math.max(0, shape.trunk.findIndex((s) => s.id === id))];
  // Satellites sit under the nearest earlier main-line station by day, side
  // by side when several share one.
  const under = new Map<number, number>();
  const satAt = (day: number) => { let k = 0; shape.trunk.forEach((s, i) => { if (s.day <= day) k = i; }); const n = under.get(k) ?? 0; under.set(k, n + 1); return xs[k] + 9 * n; };
  return (
    <svg viewBox="0 0 280 22" className={`rg ${className}`} aria-hidden="true" preserveAspectRatio="xMinYMid meet">
      <line x1={xs[0]} y1={11} x2={xs[n - 1]} y2={11} />
      {shape.lines.map((l) => {
        const x = at(l.from), len = Math.min(l.stations.length, 4);
        return (
          <g key={l.stations[0].id}>
            <path d={`M${x} 11 L${x + 10} 3 L${x + 14 + 12 * len} 3`} className={l.kind === "branch" ? "rg-branch" : ""} />
            {Array.from({ length: len }, (_, k) => <circle key={k} cx={x + 16 + 12 * k} cy={3} r={2.5} />)}
          </g>
        );
      })}
      {shape.satellites.slice(0, 6).map((s) => { const x = satAt(s.day) + 6; return <path key={s.id} d={`M${x} 11 L${x + 6} 19 L${x + 16} 19`} className="rg-sat" />; })}
      {xs.map((x, i) => <circle key={i} cx={x} cy={11} r={3.5} className={i === n - 1 ? "rg-here" : ""} />)}
    </svg>
  );
}
