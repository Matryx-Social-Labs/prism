"use client";

/**
 * The dashboard's unit (admin charts, founder decision V2): a titled panel
 * holding one chart. Where the number comes from lives behind the ⓘ — no
 * prose under every figure — and every chart can turn into the table of the
 * numbers it draws (its "table twin": identity never by colour alone, and
 * every value reachable without hovering). A panel with nothing counted yet
 * says so in the space the chart would take, rather than drawing a flat zero.
 */

import { useState } from "react";

import { InfoIcon } from "@/components/icons";

export interface TableData {
  columns: string[];
  rows: Array<Array<string | number | null>>;
}

export function InfoTip({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <details className="relative">
      <summary
        aria-label={`Where ${label} comes from`}
        className="flex h-11 w-11 cursor-pointer list-none items-center justify-center rounded-full hover:bg-[var(--sunken)] [&::-webkit-details-marker]:hidden"
        style={{ color: "var(--ink-3)" }}
      >
        <InfoIcon />
      </summary>
      <div
        className="absolute right-0 z-20 mt-1 w-72 rounded-[var(--r-md)] border p-3 text-[13px] leading-[1.5] shadow-[var(--shadow-pop)]"
        style={{ background: "var(--surface)", borderColor: "var(--line-strong)", color: "var(--ink-2)" }}
      >
        {children}
      </div>
    </details>
  );
}

export function ChartPanel({
  title,
  source,
  note,
  table,
  empty,
  className = "",
  children,
}: {
  title: string;
  /** Where the numbers are counted — shown behind the ⓘ. */
  source: string;
  note?: string | null;
  /** The chart's numbers as a table; the panel offers to show it instead. */
  table?: TableData;
  /** When set, nothing is drawn: this sentence says why. */
  empty?: string | null;
  className?: string;
  children: React.ReactNode;
}) {
  const [asTable, setAsTable] = useState(false);
  return (
    <section className={`admin-panel ${className}`} aria-label={title}>
      <header className="mb-3 flex items-start justify-between gap-3">
        <h3 className="pt-3 text-[14px] font-semibold leading-snug" style={{ color: "var(--ink)" }}>
          {title}
        </h3>
        <div className="flex shrink-0 items-center gap-1">
          {table && !empty && (
            <button
              type="button"
              aria-pressed={asTable}
              onClick={() => setAsTable((v) => !v)}
              className="h-11 rounded-full px-3 text-[12.5px] font-semibold hover:bg-[var(--sunken)]"
              style={{ color: "var(--ink-2)" }}
            >
              {asTable ? "Chart" : "Table"}
            </button>
          )}
          <InfoTip label={title}>
            {note && <p className="mb-2">{note}</p>}
            <p className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
              {source}
            </p>
          </InfoTip>
        </div>
      </header>
      {empty ? (
        <p className="flex min-h-[120px] items-center justify-center rounded-[var(--r-md)] px-4 text-center text-[14px]" style={{ background: "var(--sunken)", color: "var(--ink-2)" }}>
          {empty}
        </p>
      ) : asTable && table ? (
        <DataTable table={table} />
      ) : (
        children
      )}
    </section>
  );
}

export function DataTable({ table }: { table: TableData }) {
  return (
    <div className="max-h-[320px] overflow-auto">
      <table className="w-full border-collapse text-left font-mono text-[12px] tabular-nums">
        <thead className="sticky top-0" style={{ background: "var(--surface)" }}>
          <tr style={{ color: "var(--ink-3)" }}>
            {table.columns.map((c, i) => (
              <th key={c} scope="col" className={`py-1.5 pr-3 font-normal ${i ? "text-right" : ""}`}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((r, i) => (
            <tr key={i} className="border-t" style={{ borderColor: "var(--line)" }}>
              {r.map((v, j) =>
                j === 0 ? (
                  <th key={j} scope="row" className="py-1.5 pr-3 text-left font-normal" style={{ color: "var(--ink-2)" }}>
                    {v ?? "—"}
                  </th>
                ) : (
                  <td key={j} className="py-1.5 pr-3 text-right" style={{ color: "var(--ink)" }}>
                    {v === null || v === undefined ? "—" : typeof v === "number" ? v.toLocaleString("en-IN") : v}
                  </td>
                ),
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** A legend: a swatch and a word per series, the words in ink — identity is
 *  never carried by colour alone. `dashed` draws the period before. */
export function SeriesKey({ items }: { items: Array<{ label: string; color: string; dashed?: boolean; total?: string }> }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1.5 text-[12.5px]" style={{ color: "var(--ink-2)" }}>
      {items.map((it) => (
        <li key={it.label} className="inline-flex items-center gap-1.5">
          <svg width="14" height="8" aria-hidden className="shrink-0">
            {it.dashed ? (
              <line x1="0" x2="14" y1="4" y2="4" stroke={it.color} strokeWidth="2" strokeDasharray="3 2" />
            ) : (
              <rect width="14" height="8" rx="2" fill={it.color} />
            )}
          </svg>
          <span>{it.label}</span>
          {it.total && <span className="font-mono text-[11px] tabular-nums" style={{ color: "var(--ink)" }}>{it.total}</span>}
        </li>
      ))}
    </ul>
  );
}

/** The hover card: the day, then each value first and its name after. */
export function TipBox({ title, rows }: { title: string; rows: Array<{ label: string; value: string; color: string; dashed?: boolean }> }) {
  return (
    <div
      className="min-w-[150px] rounded-[var(--r-md)] border px-3 py-2 shadow-[var(--shadow-pop)]"
      style={{ background: "var(--surface)", borderColor: "var(--line-strong)" }}
    >
      <p className="font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>{title}</p>
      {rows.map((r) => (
        <p key={r.label} className="mt-1 flex items-center gap-2 text-[12.5px]">
          <svg width="10" height="10" aria-hidden className="shrink-0">
            {r.dashed ? (
              <line x1="0" x2="10" y1="5" y2="5" stroke={r.color} strokeWidth="2" strokeDasharray="3 2" />
            ) : (
              <rect width="10" height="10" rx="2" fill={r.color} />
            )}
          </svg>
          <span className="font-mono tabular-nums" style={{ color: "var(--ink)" }}>{r.value}</span>
          <span style={{ color: "var(--ink-2)" }}>{r.label}</span>
        </p>
      ))}
    </div>
  );
}
