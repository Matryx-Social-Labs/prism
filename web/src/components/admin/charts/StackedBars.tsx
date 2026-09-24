"use client";

/**
 * A measure split by one word (where visits came from, what happened to the
 * reports), day by day and stacked. Colours follow the validated order
 * (app/admin/admin.css); beyond six words the smallest fold into "Other", so
 * no two words ever share a colour. The legend names every colour with its
 * total — identity is never colour alone.
 */

import { Bar, BarChart, CartesianGrid, ReferenceArea, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { SeriesKey, TipBox } from "./ChartPanel";
import { SERIES, compact, dayLabel, days, figure } from "./format";
import { AXIS_TICK, CHART_H, CHART_MARGIN, uncountedSpan } from "./TrendChart";

const OTHER = "Other";

type Daily = Record<string, Array<number | null>>;

/** The words to draw, in colour order: `order` if given, else largest first;
 *  past six, the rest summed as "Other". */
export function stackKeys(series: Daily, order?: string[]): { keys: string[]; series: Daily; total: (k: string) => number } {
  const total = (k: string) => series[k].reduce<number>((a, v) => a + (v ?? 0), 0);
  const keys = order ? order.filter((k) => k in series) : Object.keys(series).sort((a, b) => total(b) - total(a));
  if (keys.length <= SERIES.length) return { keys, series, total };
  const kept = keys.slice(0, SERIES.length - 1);
  const rest = keys.slice(SERIES.length - 1);
  const len = series[keys[0]].length;
  const other = Array.from({ length: len }, (_, i) =>
    rest.every((k) => series[k][i] === null) ? null : rest.reduce((a, k) => a + (series[k][i] ?? 0), 0),
  );
  const folded: Daily = { ...Object.fromEntries(kept.map((k) => [k, series[k]])), [OTHER]: other };
  return { keys: [...kept, OTHER], series: folded, total: (k: string) => folded[k].reduce<number>((a, v) => a + (v ?? 0), 0) };
}

export function StackedBars({
  series,
  start,
  order,
  names = {},
}: {
  series: Daily;
  start: string;
  order?: string[];
  /** Words as a reader says them ("relevant" → "Kept"). */
  names?: Record<string, string>;
}) {
  const { keys, series: drawn, total } = stackKeys(series, order);
  const len = keys.length ? drawn[keys[0]].length : 0;
  const name = (k: string) => names[k] ?? k;
  const points = days(start, len).map((day, i) => ({
    label: dayLabel(day),
    // A day with no record for any word is uncounted, not zero.
    now: keys.every((k) => drawn[k][i] === null) ? null : 0,
    ...Object.fromEntries(keys.map((k) => [k, drawn[k][i]])),
  }));
  const gap = uncountedSpan(points);
  return (
    <div>
      <ResponsiveContainer width="100%" height={CHART_H}>
        <BarChart data={points} margin={CHART_MARGIN} barCategoryGap={2} maxBarSize={24} accessibilityLayer>
          <CartesianGrid vertical={false} stroke="var(--viz-grid)" />
          <XAxis dataKey="label" tick={AXIS_TICK} tickLine={false} axisLine={{ stroke: "var(--viz-grid)" }} interval="preserveStartEnd" minTickGap={28} />
          <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} width={40} allowDecimals={false} tickFormatter={(v: number) => compact(v)} />
          {gap && (
            <ReferenceArea
              x1={gap[0]}
              x2={gap[1]}
              fill="var(--viz-uncounted)"
              fillOpacity={1}
              label={{ value: "not counted", position: "insideTop", fill: "var(--ink-3)", fontSize: 11 }}
            />
          )}
          <Tooltip
            cursor={{ fill: "var(--sunken)" }}
            content={({ active, payload, label }) => {
              if (!active || !payload?.length) return null;
              const row = payload[0].payload as Record<string, number | null>;
              return (
                <TipBox
                  title={String(label)}
                  rows={[...keys].reverse().map((k) => ({
                    label: name(k),
                    value: row[k] === null ? "not counted" : figure(row[k]),
                    color: SERIES[keys.indexOf(k)],
                  }))}
                />
              );
            }}
          />
          {keys.map((k, i) => (
            <Bar key={k} dataKey={k} name={name(k)} stackId="all" fill={SERIES[i]} isAnimationActive={false} />
          ))}
        </BarChart>
      </ResponsiveContainer>
      <SeriesKey items={keys.map((k, i) => ({ label: name(k), color: SERIES[i], total: compact(total(k)) }))} />
    </div>
  );
}

/** The chart's table twin: a column per word. */
export function stackTable(series: Daily, start: string, order?: string[], names: Record<string, string> = {}) {
  const { keys, series: drawn } = stackKeys(series, order);
  const len = keys.length ? drawn[keys[0]].length : 0;
  return {
    columns: ["Day (IST)", ...keys.map((k) => names[k] ?? k)],
    rows: days(start, len).map((d, i) => [dayLabel(d), ...keys.map((k) => drawn[k][i])]),
  };
}
