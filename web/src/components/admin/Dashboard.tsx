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

import { useState } from "react";

import { SectionHead } from "@/components/SectionHead";
import type { Breakdown, MetricRow, MetricSection } from "@/lib/admin";

import { BarList, Funnel } from "./charts/Bars";
import { ChartPanel, InfoButton } from "./charts/ChartPanel";
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
/** What an empty breakdown is waiting for, where "nothing in this period" undersells it. */
const EMPTY: Record<string, string> = {
  plans: "No one is paying yet. This fills in with the first charge.",
};

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
    <ChartPanel title={b.title} source={b.source} table={table} empty={rows.length ? null : (EMPTY[b.key] ?? "Nothing in this period.")}>
      <BarList rows={rows} names={names} />
    </ChartPanel>
  );
}

/** The measures a chart does not carry, as plain numbers against the period before. */
function Figures({ rows }: { rows: MetricRow[] }) {
  const [info, setInfo] = useState(false);
  return (
    <section className="admin-panel grid content-start gap-3" aria-label="In figures">
      <header className="flex items-center gap-2">
        <h3 className="min-w-0 flex-1 text-[14.5px] font-semibold leading-[1.3]" style={{ color: "var(--ink)" }}>In figures</h3>
        <InfoButton label="these figures" open={info} onToggle={() => setInfo((v) => !v)} />
      </header>
      {info && (
        <ul className="grid gap-2 rounded-[var(--r-md)] p-2.5 text-[13px] leading-[1.45]" style={{ background: "var(--sunken)", color: "var(--ink-2)" }}>
          {rows.map((r) => (
            <li key={r.key}>
              <b className="font-semibold" style={{ color: "var(--ink)" }}>{r.label}.</b> {r.note}
              <span className="block font-mono text-[11.5px] [overflow-wrap:anywhere]">Counted in: {r.source}</span>
            </li>
          ))}
        </ul>
      )}
      <dl>
        {rows.map((r) => (
          <div key={r.key} className="flex items-baseline justify-between gap-4 border-t py-2.5" style={{ borderColor: "var(--line)" }}>
            <dt className="min-w-0 text-[13.5px]" style={{ color: "var(--ink-2)" }}>{r.label}</dt>
            <dd className="shrink-0 text-right">
              <span className="tabular-nums" style={{ font: "600 18px/1 var(--font-record)", color: r.current === null ? "var(--ink-3)" : "var(--ink)" }}>
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

/** What a section is for, in a line, where the title alone does not say. */
const HINT: Record<string, string> = {
  supply: "What Prism read and formed.",
  demand: "Where readers hit a wall.",
};

export function DashboardSection({ section, start, sub }: { section: MetricSection; start: string; sub?: string }) {
  const trends = section.rows.filter((r) => r.series);
  const plain = section.rows.filter((r) => !r.series);
  return (
    <section className="grid min-w-0 gap-3" aria-labelledby={`dash-${section.key}`}>
      <SectionHead id={`dash-${section.key}`} title={section.title} sub={sub} hint={HINT[section.key]} />
      <div className="grid grid-cols-[minmax(0,1fr)] gap-3 md:grid-cols-2 xl:grid-cols-3">
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
            className="col-span-full"
            empty={section.retention.rows.some((r) => r.by_week.some((v) => v !== null)) ? null : "No week after a sign-up has a full record yet: sign-ins are counted from the first signed-in visit, by whole weeks."}
          >
            <CohortGrid rows={section.retention.rows} />
          </ChartPanel>
        )}
        {section.lag && (
          <ChartPanel
            title={section.lag.title}
            source={section.lag.source}
            className="col-span-full"
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
