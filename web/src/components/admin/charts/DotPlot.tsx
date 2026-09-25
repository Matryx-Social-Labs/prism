/**
 * Who reports first: an outlet per row, a dot at its median hours behind the
 * first report of a shared story (left is faster), the dot sized by how many
 * stories it shared, and "first on k of n" printed beside it. HTML rows with a
 * positioned dot, so the outlet names wrap and read in order.
 */

import { compact, share } from "./format";

export interface LagRow {
  outlet: string;
  stories: number;
  first: number;
  median_hours: number;
}

const hours = (h: number) => (h < 1 ? `${Math.round(h * 60)} min` : `${h.toFixed(h < 10 ? 1 : 0)} h`);

export function DotPlot({ rows }: { rows: LagRow[] }) {
  const max = Math.max(1, ...rows.map((r) => r.median_hours));
  const most = Math.max(1, ...rows.map((r) => r.stories));
  const ticks = [0, max / 2, max];
  return (
    <div>
      <div className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-x-3 sm:grid-cols-[minmax(0,12rem)_1fr_auto]">
        <span />
        <div className="relative h-5 font-mono text-[11px]" style={{ color: "var(--viz-axis)" }} aria-hidden>
          {ticks.map((t, i) => (
            <span key={i} className="absolute top-0 whitespace-nowrap" style={{ left: `${(t / max) * 100}%`, transform: i === 0 ? "none" : i === 2 ? "translateX(-100%)" : "translateX(-50%)" }}>
              {hours(t)}
            </span>
          ))}
        </div>
        <span />
        {rows.map((r) => {
          const d = 8 + 12 * Math.sqrt(r.stories / most);
          return (
            <div key={r.outlet} className="contents">
              <span className="truncate py-2 text-[13.5px]" style={{ color: "var(--ink)" }} title={r.outlet}>
                {r.outlet}
              </span>
              <div className="relative h-6" role="img" aria-label={`${r.outlet}: ${hours(r.median_hours)} behind the first, on ${r.stories} stories`}>
                <div className="absolute inset-x-0 top-1/2 h-px" style={{ background: "var(--viz-grid)" }} />
                <div
                  className="absolute top-1/2 rounded-full"
                  style={{
                    width: d,
                    height: d,
                    left: `calc(${(r.median_hours / max) * 100}% - ${d / 2}px)`,
                    transform: "translateY(-50%)",
                    background: "var(--viz-1)",
                    opacity: 0.85,
                  }}
                />
              </div>
              <span className="whitespace-nowrap text-right font-mono text-[12px] tabular-nums" style={{ color: "var(--ink-2)" }}>
                {hours(r.median_hours)} · first {share(r.first, r.stories)}
              </span>
            </div>
          );
        })}
      </div>
      <p className="mt-2 text-[12px]" style={{ color: "var(--ink-2)" }}>
        Median time behind the first report of the same story. A bigger dot shared more stories (most: {compact(most)}).
      </p>
    </div>
  );
}
