/**
 * One headline number: its name, the figure, how it moved against the period
 * before (in words and an arrow, never red or green — colour in /admin is for
 * telling series apart), and the period's shape as a sparkline. Where it was
 * counted sits behind the ⓘ like every panel's.
 */

import { ArrowDown, ArrowUp, Dash } from "@/components/icons";

import { InfoTip } from "./ChartPanel";
import { change, figure, type Unit } from "./format";

export function Sparkline({ values }: { values: Array<number | null> }) {
  const known = values.filter((v): v is number => v !== null);
  if (known.length < 2) return null;
  const max = Math.max(1, ...known);
  const x = (i: number) => (i / (values.length - 1)) * 100;
  const y = (v: number) => 30 - (v / max) * 28;
  // A null breaks the line: no record is not a dip to zero.
  const d = values.reduce((path, v, i) => {
    if (v === null) return path;
    const move = i === 0 || values[i - 1] === null ? "M" : "L";
    return `${path}${move}${x(i).toFixed(2)},${y(v).toFixed(2)}`;
  }, "");
  return (
    <svg viewBox="0 0 100 32" preserveAspectRatio="none" className="mt-2 block h-8 w-full" aria-hidden>
      <path d={d} fill="none" stroke="var(--viz-1)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}

const DIR_ICON = { up: ArrowUp, down: ArrowDown, flat: Dash } as const;

export function KpiTile({
  label,
  current,
  previous,
  series,
  unit = "count",
  source,
  note,
}: {
  label: string;
  current: number | string | null;
  previous?: number | string | null;
  series?: Array<number | null> | null;
  unit?: Unit;
  source: string;
  note?: string | null;
}) {
  const moved = typeof current === "number" && typeof previous === "number" ? change(current, previous) : null;
  const Icon = moved ? DIR_ICON[moved.dir] : null;
  return (
    <div className="admin-panel flex flex-col">
      <div className="flex items-start justify-between gap-2">
        <h3 className="pt-3 text-[13px] font-semibold leading-snug" style={{ color: "var(--ink-2)" }}>
          {label}
        </h3>
        <InfoTip label={label}>
          {note && <p className="mb-2">{note}</p>}
          <p className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{source}</p>
        </InfoTip>
      </div>
      <p className="mt-1 text-[30px] font-semibold leading-none tabular-nums" style={{ color: current === null ? "var(--ink-3)" : "var(--ink)" }}>
        {figure(current, unit)}
      </p>
      <p className="mt-2 flex min-h-[18px] items-center gap-1 text-[12.5px]" style={{ color: "var(--ink-2)" }}>
        {current === null ? (
          "Not counted yet"
        ) : moved && Icon ? (
          <>
            <Icon size={12} />
            <span className="font-mono tabular-nums" style={{ color: "var(--ink)" }}>{moved.text}</span>
            {moved.dir !== "flat" && <span className="hidden sm:inline">vs the period before</span>}
          </>
        ) : null}
      </p>
      {series && <Sparkline values={series} />}
    </div>
  );
}
