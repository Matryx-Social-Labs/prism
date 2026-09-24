/**
 * Ranked lists and the way to paying, as plain HTML bars: a label, a bar
 * scaled to the largest, the count, and its share — "3 of 4" below 30
 * (format.share). HTML rather than a chart library so the words wrap, stay
 * selectable, and read in order to a screen reader.
 */

import { ArrowDown } from "@/components/icons";

import { SMALL_N, compact, share } from "./format";

export interface Ranked {
  label: string;
  current: number | null;
}

export function BarList({ rows, names = {}, limit = 8 }: { rows: Ranked[]; names?: Record<string, string>; limit?: number }) {
  const known = rows.filter((r): r is { label: string; current: number } => r.current !== null);
  const total = known.reduce((a, r) => a + r.current, 0);
  const max = Math.max(1, ...known.map((r) => r.current));
  const shown = known.slice(0, limit);
  const rest = known.slice(limit).reduce((a, r) => a + r.current, 0);
  const lines = rest > 0 ? [...shown, { label: `${known.length - limit} more`, current: rest }] : shown;
  return (
    <ul className="space-y-2.5">
      {lines.map((r) => (
        <li key={r.label}>
          <div className="flex items-baseline justify-between gap-3 text-[13.5px]">
            <span className="min-w-0 truncate" style={{ color: "var(--ink)" }} title={names[r.label] ?? r.label}>
              {names[r.label] ?? r.label}
            </span>
            <span className="shrink-0 font-mono text-[12px] tabular-nums" style={{ color: "var(--ink)" }}>
              {compact(r.current)}
              {total >= SMALL_N && <span style={{ color: "var(--ink-3)" }}> · {share(r.current, total)}</span>}
            </span>
          </div>
          <div className="mt-1 h-1.5 rounded-full" style={{ background: "var(--sunken)" }}>
            <div className="h-full rounded-full" style={{ width: `${(r.current / max) * 100}%`, background: "var(--viz-1)" }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

/** Steps that narrow: each bar against the first step, and between steps how
 *  many went on — counts below 30, never a rate off a handful. */
export function Funnel({ steps }: { steps: Array<{ label: string; current: number }> }) {
  const top = Math.max(1, steps[0]?.current ?? 0);
  return (
    <ol>
      {steps.map((s, i) => {
        const prev = i > 0 ? steps[i - 1].current : null;
        return (
          <li key={s.label} className={i ? "mt-1" : ""}>
            {prev !== null && (
              <p className="flex items-center gap-1 py-1 pl-3 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
                <ArrowDown size={11} />
                {prev > 0 && `${share(s.current, prev)} went on`}
              </p>
            )}
            <div className="flex items-center gap-3">
              <div className="relative h-8 flex-1 overflow-hidden rounded-[var(--r-sm)]" style={{ background: "var(--sunken)" }}>
                <div className="h-full" style={{ width: `${(s.current / top) * 100}%`, background: "var(--viz-1)" }} />
                <span className="absolute inset-y-0 left-3 flex items-center text-[13px] font-semibold" style={{ color: "var(--ink)" }}>
                  <span className="rounded px-1" style={{ background: "var(--surface)" }}>{s.label}</span>
                </span>
              </div>
              <span className="w-12 shrink-0 text-right font-mono text-[13px] tabular-nums" style={{ color: "var(--ink)" }}>
                {compact(s.current)}
              </span>
            </div>
          </li>
        );
      })}
    </ol>
  );
}
