"use client";

/**
 * "The ledger" (admin dashboard design direction, founder-approved G3,
 * 2026-09-23): the paper of record turned on Prism itself. Hairline tables, not
 * cards; ink only, with the accent reserved for what you can act on; every
 * figure followed by where it was counted. Below a count of 30 a share prints
 * as "3 of 4", never a percentage — a percentage of four readers would read as
 * a fact about a market.
 *
 * The daily strip follows the dataviz method for a single series: no legend
 * (the row names it), bars from one baseline with a 2px gap, the latest day in
 * ink and the rest one step back, a day before counting began left empty (not
 * drawn as zero), every bar its own hover target, and a day-by-day table under
 * each section as the strip's table twin.
 */

import type { Breakdown, MetricRow, MetricSection } from "@/lib/admin";

/** Below this many, a share is printed as a count. */
export const SMALL_N = 30;

const inIST = (iso: string, opts: Intl.DateTimeFormatOptions) =>
  new Date(iso.length === 10 ? `${iso}T12:00:00+05:30` : iso).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", ...opts });
export const dayLabel = (iso: string) => inIST(iso, { day: "numeric", month: "short" });

export function figure(value: number | string | null, unit: MetricRow["unit"]): string {
  if (value === null || value === undefined) return "—";
  if (unit === "time") return `${inIST(String(value), { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} IST`;
  const n = Number(value);
  if (unit === "inr") return `₹${n.toLocaleString("en-IN")}`;
  if (unit === "usd") return `$${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return n.toLocaleString("en-IN");
}

/** "3 of 4" below SMALL_N, "12%" at or above it. */
export function share(part: number, whole: number): string {
  if (whole <= 0) return "";
  return whole < SMALL_N ? `${part} of ${whole}` : `${Math.round((part / whole) * 100)}%`;
}

/** Daily values, or weekly sums when the period is long enough that a day's
 *  bar would be thinner than the gap between bars. */
function buckets(series: Array<number | null>, start: string): { label: string; value: number | null }[] {
  const day = (i: number) => {
    const d = new Date(`${start}T12:00:00+05:30`);
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  };
  if (series.length <= 35) return series.map((v, i) => ({ label: dayLabel(day(i)), value: v }));
  const out = [];
  for (let i = 0; i < series.length; i += 7) {
    const week = series.slice(i, i + 7);
    const known = week.filter((v): v is number => v !== null);
    out.push({ label: `week of ${dayLabel(day(i))}`, value: known.length ? known.reduce((a, b) => a + b, 0) : null });
  }
  return out;
}

const STRIP_W = 168;
const STRIP_H = 28;
const GAP = 2;
const MAX_BAR = 24;

export function BarStrip({ series, start, label }: { series: Array<number | null>; start: string; label: string }) {
  const bars = buckets(series, start);
  const known = bars.filter((b) => b.value !== null) as { label: string; value: number }[];
  const max = Math.max(1, ...known.map((b) => b.value));
  const w = Math.min(MAX_BAR, (STRIP_W - GAP * (bars.length - 1)) / bars.length);
  const total = known.reduce((a, b) => a + b.value, 0);
  const peak = known.reduce<{ label: string; value: number } | null>((a, b) => (a === null || b.value > a.value ? b : a), null);
  const summary = known.length
    ? `${label}: ${total.toLocaleString("en-IN")} in all${peak && peak.value > 0 ? `, most on ${peak.label} (${peak.value})` : ""}`
    : `${label}: not counted in this period`;
  return (
    <svg width={STRIP_W} height={STRIP_H} viewBox={`0 0 ${STRIP_W} ${STRIP_H}`} role="img" aria-label={summary} className="block">
      <line x1={0} x2={STRIP_W} y1={STRIP_H - 0.5} y2={STRIP_H - 0.5} stroke="var(--line)" strokeWidth={1} />
      {bars.map((b, i) => {
        const x = i * (w + GAP);
        const last = i === bars.length - 1;
        // A zero is a real, counted zero: a hairline stub. A null is no record.
        const h = b.value === null ? 0 : b.value === 0 ? 1 : Math.max(2, (b.value / max) * (STRIP_H - 2));
        return (
          <g key={i}>
            <title>{`${b.label}: ${b.value === null ? "not counted" : b.value.toLocaleString("en-IN")}`}</title>
            {/* The hit target is the whole column, not the painted pixels. */}
            <rect x={x - GAP / 2} y={0} width={w + GAP} height={STRIP_H} fill="transparent" />
            {h > 0 && (
              <rect x={x} y={STRIP_H - h} width={w} height={h} rx={Math.min(1.5, w / 2)} fill={last ? "var(--ink)" : "var(--ink-3)"} />
            )}
          </g>
        );
      })}
    </svg>
  );
}

function Source({ children }: { children: React.ReactNode }) {
  return (
    <p className="mt-0.5 font-mono text-[11px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
      {children}
    </p>
  );
}

export function LedgerSection({ section, start }: { section: MetricSection; start: string }) {
  const withSeries = section.rows.filter((r) => r.series);
  return (
    <section className="mt-12" aria-labelledby={`ledger-${section.key}`}>
      <h2 id={`ledger-${section.key}`} className="text-[21px] leading-tight" style={{ fontFamily: "var(--font-display), serif" }}>
        {section.title}
      </h2>
      {/* Fixed columns, the same in every section, so the figures of the whole
          page line up in one column — a ledger, not six tables. */}
      <table className="mt-3 w-full table-fixed border-collapse text-left">
        <colgroup>
          <col />
          <col className="w-[7.5rem]" />
          <col className="hidden w-[7.5rem] sm:table-column" />
          <col className="hidden w-[196px] md:table-column" />
        </colgroup>
        <thead>
          <tr className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
            <th scope="col" className="py-2 pr-4 font-semibold">Measure</th>
            <th scope="col" className="py-2 pr-4 text-right font-semibold">This period</th>
            <th scope="col" className="hidden py-2 pr-4 text-right font-semibold sm:table-cell">Before</th>
            <th scope="col" className="hidden py-2 font-semibold md:table-cell">By day</th>
          </tr>
        </thead>
        <tbody>
          {section.rows.map((r) => (
            <tr key={r.key} className="border-t align-top" style={{ borderColor: "var(--line)" }}>
              <th scope="row" className="py-3 pr-4 text-left font-normal">
                <span className="text-[15px]" style={{ color: "var(--ink)" }}>{r.label}</span>
                {r.note && (
                  <span className="mt-0.5 block max-w-[46ch] text-[13px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
                    {r.note}
                  </span>
                )}
                <Source>{r.source}</Source>
              </th>
              <td className="py-3 pr-4 text-right font-mono text-[17px] tabular-nums" style={{ color: "var(--ink)" }}>
                {figure(r.current, r.unit)}
              </td>
              <td className="hidden py-3 pr-4 text-right font-mono text-[14px] tabular-nums sm:table-cell" style={{ color: "var(--ink-2)" }}>
                {r.previous === null ? "" : figure(r.previous, r.unit)}
              </td>
              <td className="hidden py-3 md:table-cell">
                {r.series && <BarStrip series={r.series} start={start} label={r.label} />}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {withSeries.length > 0 && <DayByDay rows={withSeries} start={start} />}

      {section.breakdowns.length > 0 && (
        <div className="mt-6 grid gap-x-8 gap-y-6 sm:grid-cols-2 lg:grid-cols-3">
          {section.breakdowns.map((b) => (
            <BreakdownList key={b.key} b={b} />
          ))}
        </div>
      )}
      {section.retention && <Retention r={section.retention} />}
      {section.lag && <Lag lag={section.lag} />}
    </section>
  );
}

/** The strips' table twin: every day's number, reachable without hovering. */
function DayByDay({ rows, start }: { rows: MetricRow[]; start: string }) {
  const days = rows[0].series!.map((_, i) => {
    const d = new Date(`${start}T12:00:00+05:30`);
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
  return (
    <details className="mt-2">
      <summary className="min-h-[44px] cursor-pointer py-2 text-[14px] font-semibold" style={{ color: "var(--accent)" }}>
        Day by day
      </summary>
      <div className="overflow-x-auto">
        <table className="w-full border-collapse font-mono text-[12px] tabular-nums">
          <thead>
            <tr style={{ color: "var(--ink-3)" }}>
              <th scope="col" className="py-1 pr-4 text-left font-normal">DAY (IST)</th>
              {rows.map((r) => (
                <th key={r.key} scope="col" className="py-1 pr-4 text-right font-normal">{r.label.toUpperCase()}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {days.map((d, i) => (
              <tr key={d} className="border-t" style={{ borderColor: "var(--line)" }}>
                <th scope="row" className="py-1 pr-4 text-left font-normal" style={{ color: "var(--ink-2)" }}>{dayLabel(d)}</th>
                {rows.map((r) => (
                  <td key={r.key} className="py-1 pr-4 text-right" style={{ color: "var(--ink)" }}>
                    {r.series![i] === null ? "—" : r.series![i]!.toLocaleString("en-IN")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}

function BreakdownList({ b }: { b: Breakdown }) {
  const total = b.rows.reduce((a, r) => a + (r.current ?? 0), 0);
  return (
    <div>
      <h3 className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>
        {b.title}
      </h3>
      {b.rows.length === 0 ? (
        <p className="mt-2 text-[14px]" style={{ color: "var(--ink-2)" }}>Nothing yet.</p>
      ) : (
        <ul className="mt-1.5">
          {b.rows.map((r) => (
            <li key={r.label} className="flex items-baseline justify-between gap-3 border-t py-1.5 text-[14px]" style={{ borderColor: "var(--line)" }}>
              <span style={{ color: "var(--ink)" }}>{r.label}</span>
              <span className="font-mono text-[13px] tabular-nums" style={{ color: "var(--ink)" }}>
                {r.current === null ? "—" : r.current.toLocaleString("en-IN")}
                {r.current !== null && total >= SMALL_N && (
                  <span style={{ color: "var(--ink-3)" }}> · {share(r.current, total)}</span>
                )}
              </span>
            </li>
          ))}
        </ul>
      )}
      <Source>{b.source}</Source>
    </div>
  );
}

function Retention({ r }: { r: NonNullable<MetricSection["retention"]> }) {
  return (
    <div className="mt-8">
      <h3 className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>{r.title}</h3>
      <table className="mt-1.5 w-full max-w-[520px] border-collapse text-[14px]">
        <thead>
          <tr className="text-left font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
            <th scope="col" className="py-1 font-normal">WEEK OF</th>
            <th scope="col" className="py-1 text-right font-normal">SIGNED UP</th>
            <th scope="col" className="py-1 text-right font-normal">CAME BACK</th>
          </tr>
        </thead>
        <tbody>
          {r.rows.map((w) => (
            <tr key={w.week} className="border-t" style={{ borderColor: "var(--line)" }}>
              <th scope="row" className="py-1.5 text-left font-normal">{dayLabel(w.week)}</th>
              <td className="py-1.5 text-right font-mono tabular-nums">{w.accounts}</td>
              <td className="py-1.5 text-right font-mono tabular-nums" style={{ color: w.complete ? "var(--ink)" : "var(--ink-3)" }}>
                {w.accounts === 0 ? "—" : w.complete ? share(w.returned, w.accounts) : "week not over"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <Source>{r.source}</Source>
    </div>
  );
}

function Lag({ lag }: { lag: NonNullable<MetricSection["lag"]> }) {
  return (
    <div className="mt-8">
      <h3 className="text-[12.5px] font-semibold uppercase tracking-[0.06em]" style={{ color: "var(--ink-3)" }}>{lag.title}</h3>
      <p className="mt-1 max-w-[62ch] text-[13px] leading-[1.5]" style={{ color: "var(--ink-2)" }}>
        Each outlet&apos;s first report of a story, against the first report of anyone, by the time the outlet
        printed. Listed once an outlet shares {lag.min_stories} stories with others; a report a week after the first
        is a new story and is left out.
      </p>
      {lag.rows.length === 0 ? (
        <p className="mt-2 text-[14px]" style={{ color: "var(--ink-2)" }}>No outlet has shared {lag.min_stories} stories with another in this period.</p>
      ) : (
        <table className="mt-1.5 w-full max-w-[640px] border-collapse text-[14px]">
          <thead>
            <tr className="text-left font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
              <th scope="col" className="py-1 font-normal">OUTLET</th>
              <th scope="col" className="py-1 text-right font-normal">STORIES</th>
              <th scope="col" className="py-1 text-right font-normal">FIRST</th>
              <th scope="col" className="py-1 text-right font-normal">BEHIND THE FIRST (MEDIAN)</th>
            </tr>
          </thead>
          <tbody>
            {lag.rows.map((o) => (
              <tr key={o.outlet} className="border-t" style={{ borderColor: "var(--line)" }}>
                <th scope="row" className="py-1.5 text-left font-normal">{o.outlet}</th>
                <td className="py-1.5 text-right font-mono tabular-nums">{o.stories}</td>
                <td className="py-1.5 text-right font-mono tabular-nums">{share(o.first, o.stories)}</td>
                <td className="py-1.5 text-right font-mono tabular-nums">{o.median_hours} h</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <Source>{lag.source}</Source>
    </div>
  );
}
