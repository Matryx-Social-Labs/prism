import type { ArchiveReading, FeedItem } from "@/lib/api";
import { LONG_MONTHS } from "@/lib/dateline";
import { NAV_ITEMS, sectorGroup } from "@/lib/sectors";

/**
 * The day archive's calendar (audit 02, P1-2): /feed/<yyyy-mm-dd> on the IST
 * clock. Pure, so the page, the index and the sitemap agree on what a date is.
 */

const ISO_DAY = /^\d{4}-\d{2}-\d{2}$/;

/** A strict yyyy-mm-dd naming a real calendar day, else null (2026-9-27 and 2026-02-30 are not). */
export function parseDay(s: string): string | null {
  if (!ISO_DAY.test(s)) return null;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s ? s : null;
}

/** Today on the newsroom clock, yyyy-mm-dd. */
export function istToday(now: Date = new Date()): string {
  return now.toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });
}

/** "27 September 2026": a calendar date, so no zone is involved. */
export function longDay(day: string): string {
  const [y, m, d] = day.split("-").map(Number);
  return `${d} ${LONG_MONTHS[m - 1]} ${y}`;
}

const daysBetween = (from: string, to: string) => Math.round((Date.parse(`${to}T00:00:00Z`) - Date.parse(`${from}T00:00:00Z`)) / 86_400_000);

export const YOUNG_DAY_REVALIDATE = 3600;
export const SETTLED_DAY_REVALIDATE = 604_800;

/**
 * An hour while the day is under 48 hours old, then a week: a settled day is
 * nearly immutable, so its page is written once or twice, ever. Chosen from the
 * date alone, before any fetch, because the fetch's clock IS the page's clock.
 * ponytail: a day whose reading stopped and later resumed (28 Sep 2026) turns
 * settled at most a week late; key the clock on `settled` if that matters.
 */
export function dayRevalidate(day: string, today: string = istToday()): number {
  return daysBetween(day, today) <= 2 ? YOUNG_DAY_REVALIDATE : SETTLED_DAY_REVALIDATE;
}

export type SubjectGroup = { key: string | null; name: string; href: string | null; items: FeedItem[] };

/**
 * A day's records under their subject roots, in the nav's fixed order (never by
 * size), each keeping the order it came in (most outlets first). A record with
 * no subject is grouped last under words that say so — never "Other".
 */
export function bySubject(items: FeedItem[]): SubjectGroup[] {
  const rootOf = (it: FeedItem) => it.subject_path?.split(".")[0] ?? sectorGroup(it.sector)?.slug ?? null;
  const groups: SubjectGroup[] = NAV_ITEMS.map((n) => ({ key: n.key, name: n.name, href: n.href, items: items.filter((it) => rootOf(it) === n.key) }));
  const known = new Set(NAV_ITEMS.map((n) => n.key));
  const rest = items.filter((it) => !known.has(rootOf(it) ?? ""));
  return [...groups, { key: null, name: "Not yet placed in a subject", href: null, items: rest }].filter((g) => g.items.length > 0);
}

export type ArchiveRow = { kind: "day"; day: ArchiveReading } | { kind: "gap"; from: string; to: string };

/** The index's rows, newest first: each day read, and each run of days not read as one row. */
export function archiveRows(days: ArchiveReading[]): ArchiveRow[] {
  return days.reduce<ArchiveRow[]>((out, day) => {
    const last = out[out.length - 1];
    if (day.read) return [...out, { kind: "day", day }];
    if (last?.kind === "gap") return [...out.slice(0, -1), { ...last, from: day.date }];
    return [...out, { kind: "gap", from: day.date, to: day.date }];
  }, []);
}
