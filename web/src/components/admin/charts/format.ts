// Formatting shared by every admin chart: IST days, figures by unit, and the
// small-n rule (below 30, a share is a count — a percentage of four readers
// reads as a fact about a market).

export const SMALL_N = 30;

/** Categorical slots, in the validated order (app/admin/admin.css). */
export const SERIES = ["var(--viz-1)", "var(--viz-2)", "var(--viz-3)", "var(--viz-4)", "var(--viz-5)", "var(--viz-6)"];

export type Unit = "count" | "inr" | "usd" | "time";

const inIST = (iso: string, opts: Intl.DateTimeFormatOptions) =>
  new Date(iso.length === 10 ? `${iso}T12:00:00+05:30` : iso).toLocaleString("en-IN", { timeZone: "Asia/Kolkata", ...opts });

export const dayLabel = (iso: string) => inIST(iso, { day: "numeric", month: "short" });

/** The IST calendar days from `start`, `n` of them, as YYYY-MM-DD. */
export function days(start: string, n: number): string[] {
  return Array.from({ length: n }, (_, i) => {
    const d = new Date(`${start}T12:00:00+05:30`);
    d.setDate(d.getDate() + i);
    return d.toISOString().slice(0, 10);
  });
}

export function figure(value: number | string | null | undefined, unit: Unit = "count"): string {
  if (value === null || value === undefined) return "—";
  if (unit === "time") return `${inIST(String(value), { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" })} IST`;
  const n = Number(value);
  if (unit === "inr") return `₹${n.toLocaleString("en-IN")}`;
  if (unit === "usd") return `$${n.toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return n.toLocaleString("en-IN");
}

/** Compact for axes and tiles: 1,284 · 12.9K · 4.2M. */
export function compact(n: number): string {
  return Math.abs(n) < 10_000 ? n.toLocaleString("en-IN") : new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }).format(n);
}

/** "3 of 4" below SMALL_N, "12%" at or above it. */
export function share(part: number, whole: number): string {
  if (whole <= 0) return "";
  return whole < SMALL_N ? `${part} of ${whole}` : `${Math.round((part / whole) * 100)}%`;
}

/** Change against the period before, in words a founder reads at a glance.
 *  Never a percentage off a small base: "+3 from 4" rather than "+75%". */
export function change(now: number | null, before: number | null): { text: string; dir: "up" | "down" | "flat" } | null {
  if (now === null || before === null) return null;
  const d = now - before;
  const dir = d > 0 ? "up" : d < 0 ? "down" : "flat";
  if (d === 0) return { text: "same as before", dir };
  const sign = d > 0 ? "+" : "−";
  const size = before >= SMALL_N ? `${Math.round((Math.abs(d) / before) * 100)}%` : `${compact(Math.abs(d))} from ${compact(before)}`;
  return { text: `${sign}${size}`, dir };
}
