/**
 * Retention as a cohort grid: a row per sign-up week, a column per week after,
 * each cell the number of that week's accounts who used Prism signed in. The
 * cell is shaded by the share (one hue, light to dark), but prints the count —
 * a cohort of three is not a percentage. A week with no full record — not
 * over yet, or begun before sign-ins were counted — is left blank with a
 * dashed edge, never drawn as a zero (common/metrics.retention).
 */

import { dayLabel, share } from "./format";

export interface CohortRow {
  week: string;
  accounts: number;
  by_week: Array<number | null>;
}

/** 0 for no one, else 1–5 by the share of the cohort that came back. */
export function step(returned: number, accounts: number): number {
  if (accounts <= 0 || returned <= 0) return 0;
  return Math.min(5, Math.max(1, Math.ceil((returned / accounts) * 5)));
}

export function CohortGrid({ rows }: { rows: CohortRow[] }) {
  const cols = rows[0]?.by_week.length ?? 0;
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-separate text-center font-mono text-[12px] tabular-nums" style={{ borderSpacing: 3 }}>
        <thead>
          <tr style={{ color: "var(--ink-3)" }}>
            <th scope="col" className="pb-1 text-left font-normal">WEEK OF</th>
            <th scope="col" className="pb-1 pr-2 text-right font-normal">SIGNED UP</th>
            {Array.from({ length: cols }, (_, k) => (
              <th key={k} scope="col" className="pb-1 font-normal">+{k + 1}w</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.week}>
              <th scope="row" className="whitespace-nowrap pr-2 text-left font-normal" style={{ color: "var(--ink-2)" }}>
                {dayLabel(r.week)}
              </th>
              <td className="pr-2 text-right" style={{ color: "var(--ink)" }}>{r.accounts}</td>
              {r.by_week.map((v, k) => {
                const title =
                  v === null ? `Week ${k + 1} after: no record yet` : r.accounts ? `Week ${k + 1} after: ${share(v, r.accounts)} came back` : "No sign-ups that week";
                if (v === null)
                  return (
                    <td key={k} title={title} aria-label={title} className="h-8 min-w-[36px] rounded-[var(--r-sm)]" style={{ border: "1px dashed var(--line-strong)" }} />
                  );
                const s = r.accounts ? step(v, r.accounts) : 0;
                return (
                  <td
                    key={k}
                    title={title}
                    className="h-8 min-w-[36px] rounded-[var(--r-sm)]"
                    style={{
                      background: s ? `var(--viz-seq-${s})` : "var(--sunken)",
                      color: s >= 4 ? `var(--viz-seq-on-${s})` : r.accounts ? "var(--ink)" : "var(--ink-3)",
                    }}
                  >
                    {r.accounts ? v : "—"}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      <p className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[12px]" style={{ color: "var(--ink-2)" }}>
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden className="inline-block h-3 w-3 rounded-[3px]" style={{ border: "1px dashed var(--line-strong)" }} />
          no record: not over, or before counting began
        </span>
        <span className="inline-flex items-center gap-1.5">
          <span aria-hidden className="inline-flex">
            {[1, 2, 3, 4, 5].map((s) => (
              <span key={s} className="inline-block h-3 w-3" style={{ background: `var(--viz-seq-${s})` }} />
            ))}
          </span>
          fewer to more of the week came back
        </span>
      </p>
    </div>
  );
}
