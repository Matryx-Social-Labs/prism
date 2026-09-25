"use client";

/**
 * One measure over the period, day by day (IST), with the period before laid
 * over it as a dashed line — the comparison is in the picture, not in a
 * second number to hold in your head. Days before counting began are hatched
 * and left undrawn (the key says so): an empty stretch is "no record", never a
 * zero. The last counted day carries a dot; hovering reads out the day, its
 * value and the same day of the period before.
 */

import { useId } from "react";
import { Area, CartesianGrid, ComposedChart, Line, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { SeriesKey, TipBox } from "./ChartPanel";
import { compact, dayLabel, days, figure, type Unit } from "./format";

export const AXIS_TICK = { fill: "var(--viz-axis)", fontSize: 11, fontFamily: "var(--font-mono), monospace" };
export const CHART_H = 180;
/** Room on the right for the last day's label. */
export const CHART_MARGIN = { top: 8, right: 28, bottom: 0, left: 0 };

interface Point {
  day: string;
  label: string;
  now: number | null;
  before: number | null;
}

/** Days with no record are hatched, never drawn as zero; the key says so. */
export const UNCOUNTED_KEY = { label: "Hatched: not counted yet, never zero", color: "", hatched: true };
export const useHatchId = () => `hatch${useId().replace(/:/g, "")}`;
/** An SVG hatch for a chart's <defs> (the token hatch is a CSS gradient, which SVG cannot fill with). */
export const hatchDefs = (id: string) => (
  <defs>
    <pattern id={id} width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
      <rect width="8" height="8" fill="var(--viz-uncounted)" />
      <line x1="0" y1="0" x2="0" y2="8" stroke="var(--line-strong)" strokeWidth="1" />
    </pattern>
  </defs>
);

/** The leading run of days with no record, as [first, last] labels. */
export function uncountedSpan(points: Array<{ label: string; now: number | null }>): [string, string] | null {
  const n = points.findIndex((p) => p.now !== null);
  const end = n === -1 ? points.length : n;
  return end > 0 ? [points[0].label, points[end - 1].label] : null;
}

/** A counted day whose neighbours both have no record. */
export const isolated = (series: Array<number | null>, i: number) =>
  series[i] !== null && series[i - 1] == null && series[i + 1] == null;

export function TrendChart({
  series,
  prev,
  start,
  label,
  unit = "count",
  cumulative = false,
}: {
  series: Array<number | null>;
  prev?: Array<number | null> | null;
  start: string;
  label: string;
  unit?: Unit;
  /** A running total: no "period before" line, and the axis need not start at zero. */
  cumulative?: boolean;
}) {
  const points: Point[] = days(start, series.length).map((day, i) => ({
    day,
    label: dayLabel(day),
    now: series[i],
    before: prev?.[i] ?? null,
  }));
  const hasPrev = !cumulative && !!prev && prev.some((v) => v !== null);
  const gap = uncountedSpan(points);
  const last = series.reduce<number>((at, v, i) => (v === null ? at : i), -1);
  const hatch = useHatchId();
  const key = [
    ...(hasPrev
      ? [
          { label: "This period", color: "var(--viz-1)" },
          { label: "Period before", color: "var(--viz-prev)", dashed: true },
        ]
      : []),
    ...(gap ? [UNCOUNTED_KEY] : []),
  ];
  return (
    <div>
      <ResponsiveContainer width="100%" height={CHART_H}>
        <ComposedChart data={points} margin={CHART_MARGIN} accessibilityLayer>
          {hatchDefs(hatch)}
          <CartesianGrid vertical={false} stroke="var(--viz-grid)" />
          <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: "var(--viz-grid)" }} interval="preserveStartEnd" minTickGap={28} />
          <YAxis
            tick={AXIS_TICK}
            tickLine={false}
            axisLine={false}
            width={40}
            allowDecimals={false}
            domain={cumulative ? ["auto", "auto"] : [0, "auto"]}
            tickFormatter={(v: number) => compact(v)}
          />
          {gap && (
            <ReferenceArea
              x1={gap[0]}
              x2={gap[1]}
              fill={`url(#${hatch})`}
              fillOpacity={1}
              ifOverflow="extendDomain"
            />
          )}
          <Tooltip
            cursor={{ stroke: "var(--line-strong)" }}
            content={({ active, payload }) => {
              const p = active && payload?.[0] ? (payload[0].payload as Point) : null;
              if (!p) return null;
              const rows = [{ label, value: p.now === null ? "not counted" : figure(p.now, unit), color: "var(--viz-1)" }];
              if (hasPrev) rows.push({ label: "same day, period before", value: p.before === null ? "not counted" : figure(p.before, unit), color: "var(--viz-prev)" });
              return <TipBox title={p.label} rows={rows.map((r, i) => ({ ...r, dashed: i === 1 }))} />;
            }}
          />
          <Area
            type="linear"
            dataKey="now"
            name={label}
            stroke="var(--viz-1)"
            strokeWidth={2}
            fill="none"
            isAnimationActive={false}
            // The last counted day, and a day with no neighbour on record (no
            // line would show it), carry a dot so they are seen.
            dot={(d: { index: number; cx?: number; cy?: number }) =>
              (d.index === last || isolated(series, d.index)) && d.cx !== undefined && d.cy !== undefined ? (
                <circle key={d.index} cx={d.cx} cy={d.cy} r={d.index === last ? 4 : 3} fill="var(--viz-1)" stroke="var(--surface)" strokeWidth={2} />
              ) : (
                <g key={d.index} />
              )
            }
            activeDot={{ r: 4, strokeWidth: 0, fill: "var(--viz-1)" }}
          />
          {hasPrev && (
            <Line
              type="linear"
              dataKey="before"
              name="Period before"
              stroke="var(--viz-prev)"
              strokeWidth={1.5}
              strokeDasharray="4 4"
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      {key.length > 0 && <SeriesKey items={key} />}
    </div>
  );
}

/** The chart's table twin. */
export function trendTable(series: Array<number | null>, prev: Array<number | null> | null | undefined, start: string, label: string) {
  const withPrev = !!prev && prev.some((v) => v !== null);
  return {
    columns: ["Day (IST)", label, ...(withPrev ? ["Period before"] : [])],
    rows: days(start, series.length).map((d, i) => [dayLabel(d), series[i], ...(withPrev ? [prev![i] ?? null] : [])]),
  };
}
