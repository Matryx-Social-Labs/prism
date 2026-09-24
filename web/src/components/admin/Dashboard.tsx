"use client";

/**
 * A section of the overview, drawn from what the API sends (common/metrics.py)
 * rather than a hand-kept list, so a measure added there appears here:
 *   a row with a daily series        → a trend, the period before dashed under it
 *   a breakdown with daily series    → stacked bars
 *   any other breakdown              → a ranked bar list (the way to paying: a funnel)
 *   retention, who reports first     → the cohort grid, the dot plot
 *   rows with no series              → "In figures", one panel of plain numbers
 * Every panel keeps its source behind the ⓘ and its numbers one tap away as a
 * table (ChartPanel).
 */

import type { Breakdown, MetricRow, MetricSection } from "@/lib/admin";

import { BarList, Funnel } from "./charts/Bars";
import { ChartPanel, InfoTip } from "./charts/ChartPanel";
import { CohortGrid } from "./charts/CohortGrid";
import { DotPlot } from "./charts/DotPlot";
import { figure } from "./charts/format";
import { StackedBars, stackTable } from "./charts/StackedBars";
import { TrendChart, trendTable } from "./charts/TrendChart";

/** A running total, drawn without a "period before" and off a zero floor. */
const CUMULATIVE = new Set(["accounts"]);

/** Words as a founder says them. */
const NAMES: Record<string, Record<string, string>> = {
  report_status: { relevant: "Kept", duplicate: "Duplicate", rejected: "Not relevant", pending: "Not read yet" },
};

const NOT_YET = "Not counted yet: counting begins with the first visit.";

function Trend({ row, start }: { row: MetricRow; start: string }) {
  const series = row.series!;
  const prev = CUMULATIVE.has(row.key) ? null : row.prev_series;
  return (
    <ChartPanel
      title={row.label}
      source={row.source}
      note={row.note}
      // Days before counting began are shaded in the chart; only a period
      // with no record at all is left undrawn.
      empty={series.some((v) => v !== null) ? null : NOT_YET}
      table={trendTable(series, prev, start, row.label)}
    >
      <TrendChart series={series} prev={prev} start={start} label={row.label} unit={row.unit} cumulative={CUMULATIVE.has(row.key)} />
    </ChartPanel>
  );
}

function Split({ b, start }: { b: Breakdown; start: string }) {
  const names = NAMES[b.key] ?? {};
  const rows = b.rows.filter((r) => r.current !== null && r.current > 0);
  const table = { columns: ["", "This period"], rows: b.rows.map((r) => [names[r.label] ?? r.label, r.current]) };
  if (b.series && Object.keys(b.series).length > 0) {
    // Fixed order where the API gives one (kept first, then what was filtered).
    const order = b.key === "report_status" ? Object.keys(b.series) : undefined;
    const drawn = Object.values(b.series).some((v) => v.some((x) => x !== null));
    return (
      <ChartPanel title={b.title} source={b.source} table={stackTable(b.series, start, order, names)} empty={drawn ? null : NOT_YET}>
        <StackedBars series={b.series} start={start} order={order} names={names} />
      </ChartPanel>
    );
  }
  const counted = b.rows.some((r) => r.current !== null);
  if (b.key === "funnel") {
    return (
      <ChartPanel title={b.title} source={b.source} table={table} empty={counted ? null : NOT_YET}>
        <Funnel steps={b.rows.map((r) => ({ label: r.label, current: r.current ?? 0 }))} />
      </ChartPanel>
    );
  }
  return (
    <ChartPanel title={b.title} source={b.source} table={table} empty={rows.length ? null : "Nothing in this period."}>
      <BarList rows={rows} names={names} />
    </ChartPanel>
  );
}

/** The measures a chart does not carry, as plain numbers against the period before. */
function Figures({ rows }: { rows: MetricRow[] }) {
  return (
    <section className="admin-panel" aria-label="In figures">
      <header className="mb-2 flex items-start justify-between gap-3">
        <h3 className="pt-1.5 text-[14px] font-semibold" style={{ color: "var(--ink)" }}>In figures</h3>
        <InfoTip label="these figures">
          <ul className="space-y-2">
            {rows.map((r) => (
              <li key={r.key}>
                <strong style={{ color: "var(--ink)" }}>{r.label}.</strong> {r.note}
                <span className="block font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{r.source}</span>
              </li>
            ))}
          </ul>
        </InfoTip>
      </header>
      <dl>
        {rows.map((r) => (
          <div key={r.key} className="flex items-baseline justify-between gap-4 border-t py-2.5" style={{ borderColor: "var(--line)" }}>
            <dt className="text-[13.5px]" style={{ color: "var(--ink-2)" }}>{r.label}</dt>
            <dd className="text-right">
              <span className="font-mono text-[15px] tabular-nums" style={{ color: r.current === null ? "var(--ink-3)" : "var(--ink)" }}>
                {figure(r.current, r.unit)}
              </span>
              {r.previous !== null && r.current !== null && (
                <span className="ml-2 font-mono text-[11px] tabular-nums" style={{ color: "var(--ink-3)" }}>
                  before {figure(r.previous, r.unit)}
                </span>
              )}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

export function DashboardSection({ section, start }: { section: MetricSection; start: string }) {
  const trends = section.rows.filter((r) => r.series);
  const plain = section.rows.filter((r) => !r.series);
  return (
    <section className="mt-12" aria-labelledby={`dash-${section.key}`}>
      <h2 id={`dash-${section.key}`} className="text-[21px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        {section.title}
      </h2>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {trends.map((r) => (
          <Trend key={r.key} row={r} start={start} />
        ))}
        {section.breakdowns.map((b) => (
          <Split key={b.key} b={b} start={start} />
        ))}
        {plain.length > 0 && <Figures rows={plain} />}
        {section.retention && (
          <ChartPanel
            title={section.retention.title}
            source={section.retention.source}
            className="lg:col-span-2"
            empty={section.retention.rows.some((r) => r.by_week.some((v) => v !== null)) ? null : "No week after a sign-up has a full record yet: sign-ins are counted from the first signed-in visit, by whole weeks."}
          >
            <CohortGrid rows={section.retention.rows} />
          </ChartPanel>
        )}
        {section.lag && (
          <ChartPanel
            title={section.lag.title}
            source={section.lag.source}
            className="lg:col-span-2"
            note={`Each outlet's first report of a story against the first report of anyone, by the time the outlet printed. Listed once an outlet shares ${section.lag.min_stories} stories with others; a report a week after the first is a new story and is left out.`}
            empty={section.lag.rows.length ? null : `No outlet has shared ${section.lag.min_stories} stories with another in this period.`}
            table={{
              columns: ["Outlet", "Stories", "First on", "Median hours behind"],
              rows: section.lag.rows.map((o) => [o.outlet, o.stories, o.first, o.median_hours]),
            }}
          >
            <DotPlot rows={section.lag.rows} />
          </ChartPanel>
        )}
      </div>
    </section>
  );
}
