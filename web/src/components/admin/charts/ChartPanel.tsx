"use client";

/**
 * The dashboard's unit (admin charts, founder decision V2): a titled panel
 * holding one chart. Where the number comes from opens under the ⓘ as
 * "Counted in: <source>" — no prose under every figure — and every chart can
 * turn into the table of the numbers it draws (its "table twin": identity
 * never by colour alone, and every value reachable without hovering). A panel
 * with nothing counted yet says so, hatched, in the space the chart would
 * take, rather than drawing a flat zero.
 */

import { useState } from "react";

import { InfoIcon } from "@/components/icons";

export interface TableData {
  columns: string[];
  rows: Array<Array<string | number | null>>;
  /** Columns of words (a language), set in the reading voice rather than as figures. */
  text?: number[];
}

/** The ⓘ: opens "Counted in" under the panel's header. */
export function InfoButton({ label, open, onToggle }: { label: string; open: boolean; onToggle: () => void }) {
  return (
    <button
      type="button"
      className="p-iconbtn -my-2 shrink-0"
      aria-expanded={open}
      aria-label={`Where ${label} is counted`}
      onClick={onToggle}
    >
      <InfoIcon size={15} />
    </button>
  );
}

export function CountedIn({ source, note }: { source: string; note?: string | null }) {
  return (
    <p className="rounded-[var(--r-md)] p-2.5 text-[13px] leading-[1.45]" style={{ background: "var(--sunken)", color: "var(--ink-2)" }}>
      <b className="font-semibold">Counted in:</b>{" "}
      <span className="font-mono text-[11.5px] [overflow-wrap:anywhere]">{source}</span>
      {note && (
        <>
          <br />
          {note}
        </>
      )}
    </p>
  );
}

/** Nothing to draw: the reason, on a hatched ground with a dashed edge. */
export function Uncounted({ children }: { children: React.ReactNode }) {
  return (
    <p
      className="flex min-h-[96px] items-center justify-center rounded-[var(--r-md)] px-4 py-5 text-center text-[13.5px] leading-[1.5]"
      style={{ border: "1px dashed var(--line-strong)", background: "var(--data-uncounted)", color: "var(--ink-3)" }}
    >
      {children}
    </p>
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
  const [info, setInfo] = useState(false);
  return (
    <section className={`admin-panel grid grid-cols-[minmax(0,1fr)] content-start gap-3 ${className}`} aria-label={title}>
      <header className="flex items-center gap-2">
        <h3 className="min-w-0 flex-1 text-[14.5px] font-semibold leading-[1.3]" style={{ color: "var(--ink)" }}>
          {title}
        </h3>
        <InfoButton label={title} open={info} onToggle={() => setInfo((v) => !v)} />
        {table && !empty && (
          <button
            type="button"
            className="p-chip max-sm:min-h-[44px]"
            aria-pressed={asTable}
            onClick={() => setAsTable((v) => !v)}
            style={{ minHeight: 30, padding: "0 10px", fontSize: 12.5 }}
          >
            Table
          </button>
        )}
      </header>
      {info && <CountedIn source={source} note={note} />}
      {empty ? <Uncounted>{empty}</Uncounted> : asTable && table ? <DataTable table={table} /> : <div className="min-w-0">{children}</div>}
    </section>
  );
}

/** A row's name reads as a cell, not as the column heads' caps. */
const ROW_HEAD: React.CSSProperties = {
  font: "var(--t-body-s)",
  textTransform: "none",
  letterSpacing: 0,
  color: "var(--ink)",
  padding: 10,
  borderBottom: "1px solid var(--line)",
};

export function DataTable({ table }: { table: TableData }) {
  return (
    <div className="max-h-[320px] overflow-auto">
      <table className="p-table">
        <thead className="sticky top-0" style={{ background: "var(--surface)" }}>
          <tr>
            {table.columns.map((c, i) => (
              <th key={c} scope="col" className={i && !table.text?.includes(i) ? "num" : undefined}>
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((r, i) => (
            <tr key={i}>
              {r.map((v, j) =>
                j === 0 ? (
                  <th key={j} scope="row" className="[overflow-wrap:anywhere]" style={ROW_HEAD}>
                    {v ?? "—"}
                  </th>
                ) : (
                  <td key={j} className={table.text?.includes(j) ? undefined : "num"} style={{ color: "var(--ink)" }}>
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
export function SeriesKey({ items }: { items: Array<{ label: string; color: string; dashed?: boolean; hatched?: boolean; total?: string }> }) {
  return (
    <ul className="mt-3 flex flex-wrap gap-x-3.5 gap-y-1" style={{ font: "500 12.5px/1.3 var(--font-read)", color: "var(--ink-2)" }}>
      {items.map((it) => (
        <li key={it.label} className="inline-flex items-center gap-1.5">
          {it.hatched ? (
            <span aria-hidden className="h-2.5 w-3.5 shrink-0 border" style={{ background: "var(--data-uncounted), var(--sunken)", borderColor: "var(--line-strong)" }} />
          ) : (
            <svg width={it.dashed ? 14 : 10} height="10" aria-hidden className="shrink-0">
              {it.dashed ? (
                <line x1="0" x2="14" y1="5" y2="5" stroke={it.color} strokeWidth="2" strokeDasharray="3 2" />
              ) : (
                <rect width="10" height="10" rx="2" fill={it.color} />
              )}
            </svg>
          )}
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
      className="min-w-[150px] rounded-[var(--r-md)] border px-3 py-2"
      style={{ background: "var(--elevated)", borderColor: "var(--line-strong)", boxShadow: "var(--shadow-2)" }}
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
