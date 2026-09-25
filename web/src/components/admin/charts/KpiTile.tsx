"use client";

/**
 * One headline number: its name, the figure, how it moved against the period
 * before (an arrow and a word, never red or green — colour in /admin is for
 * telling series apart), and the period's shape as a sparkline. Where it was
 * counted opens under the ⓘ like every panel's.
 *
 * Nothing before to compare with is not "no change": the line is left out, or
 * says from when counting began. Below 30 a change is "+3 from 4", never a
 * percentage (format.change).
 */

import { useState } from "react";

import { ArrowDown, ArrowUp, Dash } from "@/components/icons";

import { CountedIn, InfoButton } from "./ChartPanel";
import { change, dayLabel, figure, type Unit } from "./format";

export function Sparkline({ values }: { values: Array<number | null> }) {
  const known = values.filter((v): v is number => v !== null);
  if (known.length < 2) return null;
  const max = Math.max(1, ...known);
  const x = (i: number) => (i / (values.length - 1)) * 100;
  const y = (v: number) => 22 - (v / max) * 20;
  // A null breaks the line: no record is not a dip to zero.
  const d = values.reduce((path, v, i) => {
    if (v === null) return path;
    const move = i === 0 || values[i - 1] === null ? "M" : "L";
    return `${path}${move}${x(i).toFixed(2)},${y(v).toFixed(2)}`;
  }, "");
  return (
    <svg viewBox="0 0 100 24" preserveAspectRatio="none" className="block h-6 w-full" aria-hidden>
      <path d={d} fill="none" stroke="var(--viz-1)" strokeWidth={1.5} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
    </svg>
  );
}

const MOVE = {
  up: { Icon: ArrowUp, word: "up" },
  down: { Icon: ArrowDown, word: "down" },
  flat: { Icon: Dash, word: "no change" },
} as const;

export function KpiTile({
  label,
  current,
  previous,
  series,
  unit = "count",
  source,
  note,
  countedSince,
}: {
  label: string;
  current: number | string | null;
  previous?: number | string | null;
  series?: Array<number | null> | null;
  unit?: Unit;
  source: string;
  note?: string | null;
  /** The IST day counting began, when that is why there is no period before. */
  countedSince?: string | null;
}) {
  const [info, setInfo] = useState(false);
  const moved = typeof current === "number" && typeof previous === "number" ? change(current, previous) : null;
  return (
    <div className="admin-panel grid grid-cols-[minmax(0,1fr)] content-start gap-2">
      <div className="flex items-center gap-1.5">
        <h3 className="min-w-0 flex-1 text-[13px] font-semibold leading-[1.25]" style={{ color: "var(--ink-2)" }}>
          {label}
        </h3>
        <InfoButton label={label} open={info} onToggle={() => setInfo((v) => !v)} />
      </div>
      {info && <CountedIn source={source} note={note} />}
      <p
        className="tabular-nums [overflow-wrap:anywhere]"
        style={{ font: "600 32px/1 var(--font-record)", letterSpacing: "-0.02em", color: current === null ? "var(--ink-3)" : "var(--ink)" }}
      >
        {figure(current, unit)}
      </p>
      <Moved current={current} moved={moved} countedSince={previous == null ? countedSince : null} />
      {series && <Sparkline values={series} />}
    </div>
  );
}

function Moved({
  current,
  moved,
  countedSince,
}: {
  current: number | string | null;
  moved: ReturnType<typeof change>;
  countedSince?: string | null;
}) {
  if (current === null) return <span className="p-count">Not counted yet</span>;
  if (!moved) return countedSince ? <span className="p-count whitespace-normal">Not counted before {dayLabel(countedSince)}</span> : null;
  const { Icon, word } = MOVE[moved.dir];
  return (
    <span className="inline-flex flex-wrap items-center gap-1 text-[12.5px] font-medium leading-[1.2]" style={{ color: "var(--ink-2)" }}>
      <Icon size={12} />
      {word}
      {moved.dir !== "flat" && <span className="font-mono text-[11.5px] tabular-nums">{moved.text}</span>}
    </span>
  );
}
