"use client";

import { useMemo, useState } from "react";
import type { StoryDevelopment } from "@/lib/api";
import { shortDate } from "@/lib/dateline";

/**
 * Sources per day (Design System v2 · structure/AttentionChart): one bar per
 * calendar day of the story, its height the sources behind the developments
 * that happened that day. A day Prism has no count for — no dated development
 * on it, or one from a payload that predates per-development counts — is
 * hatched and labelled "not counted", never drawn as a zero. A Table toggle
 * gives the same figures as rows, so nothing here is only a picture.
 */
export type AttentionDay = { day: string; n: number | null };

const DAY_MS = 86_400_000;
const IST_MS = 5.5 * 3_600_000;
/** More days than this and the per-bar figures crowd: the table carries them. */
const LABEL_MAX = 14;

/** The story's days, first dated development to last, with each day's sources or null. */
export function attentionDays(developments: StoryDevelopment[]): AttentionDay[] {
  const byDay = new Map<string, number | null>();
  for (const d of developments) {
    if (!d.occurred_at) continue;
    const t = Date.parse(d.occurred_at);
    if (Number.isNaN(t)) continue;
    // A bare date is already the day; a timestamp is read on the newsroom (IST) clock.
    const key = d.occurred_at.length === 10 ? d.occurred_at : new Date(t + IST_MS).toISOString().slice(0, 10);
    const prev = byDay.has(key) ? byDay.get(key)! : 0;
    // One development without a count leaves its whole day uncounted.
    byDay.set(key, prev == null || d.source_count == null ? null : prev + d.source_count);
  }
  if (!byDay.size) return [];
  const keys = [...byDay.keys()].sort();
  const first = Date.parse(keys[0]), last = Date.parse(keys[keys.length - 1]);
  const out: AttentionDay[] = [];
  for (let t = first; t <= last; t += DAY_MS) {
    const key = new Date(t).toISOString().slice(0, 10);
    out.push({ day: key, n: byDay.has(key) ? byDay.get(key)! : null });
  }
  return out;
}

export function Attention({ developments, height = 110 }: { developments: StoryDevelopment[]; height?: number }) {
  const days = useMemo(() => attentionDays(developments), [developments]);
  const [table, setTable] = useState(false);
  if (days.length === 0) return null;
  const max = Math.max(1, ...days.map((d) => d.n ?? 0));
  const figures = days.length <= LABEL_MAX;
  const label = (d: AttentionDay) => shortDate(`${d.day}T12:00:00Z`).toUpperCase();

  return (
    <figure className="grid gap-2">
      <div className="flex items-center">
        <figcaption style={{ font: "600 13px/1.2 var(--font-read)" }}>Attention · sources per day</figcaption>
        <button type="button" onClick={() => setTable((v) => !v)} aria-pressed={table} className="p-link ml-auto inline-flex min-h-11 items-center text-[12.5px]">
          {table ? "Chart" : "Table"}
        </button>
      </div>
      {table ? (
        <table className="p-table">
          <thead><tr><th>Day</th><th className="num">Sources</th></tr></thead>
          <tbody>
            {days.map((d) => (
              <tr key={d.day}><td>{label(d)}</td><td className="num">{d.n == null ? "Not counted" : d.n}</td></tr>
            ))}
          </tbody>
        </table>
      ) : (
        <>
          <div
            className="grid items-end gap-1"
            style={{ gridTemplateColumns: `repeat(${days.length}, minmax(0, 1fr))`, height: height + (figures ? 20 : 0) }}
            role="img"
            aria-label={`Sources per day over ${days.length} ${days.length === 1 ? "day" : "days"}; the table gives each figure`}
          >
            {days.map((d) => (
              <div key={d.day} className="grid min-w-0 content-end justify-items-center gap-1" title={`${label(d)} · ${d.n == null ? "not counted" : `${d.n} sources`}`}>
                {figures && <span className="font-mono text-[10.5px] leading-none" style={{ color: "var(--ink-3)" }}>{d.n ?? "—"}</span>}
                {d.n == null ? (
                  <span className="block w-full" style={{ height, background: "var(--data-uncounted)", border: "1px dashed var(--line-strong)" }} />
                ) : (
                  <span className="block w-full" style={{ height: Math.max(2, (d.n / max) * height), background: "var(--ink)" }} />
                )}
              </div>
            ))}
          </div>
          <div className="flex justify-between gap-2 font-mono text-[11px]" style={{ color: "var(--ink-3)" }}>
            <span>{label(days[0])}</span>
            {days.length > 1 && <span>{label(days[days.length - 1])}</span>}
          </div>
          {days.some((d) => d.n == null) && (
            <p className="flex items-center gap-1.5" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
              <span aria-hidden className="inline-block h-2.5 w-2.5" style={{ background: "var(--data-uncounted)", border: "1px dashed var(--line-strong)" }} />
              Hatched: a day not counted
            </p>
          )}
        </>
      )}
    </figure>
  );
}
