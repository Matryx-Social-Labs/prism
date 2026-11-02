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

const WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const utc = (day: string) => new Date(`${day}T00:00:00Z`);
const plusDays = (day: string, n: number) => new Date(utc(day).getTime() + n * 86_400_000).toISOString().slice(0, 10);

export type StripDay = { date: string; label: string; href: string | null; read: boolean; count: number | null; current: boolean };

/**
 * The day strip under Today and every day page: today, then the days read
 * before it, `size` wide and keeping the day being read in view. Before it,
 * yesterday's record was reachable only from the desktop footer (2026-11-02).
 * A day Prism was not reading is listed but not linked and has no count.
 */
export function dayStrip(days: ArchiveReading[], current: string | null, today: string, size = 7): StripDay[] {
  const yesterday = plusDays(today, -1);
  const all: StripDay[] = [
    { date: today, label: "Today", href: "/feed", read: true, count: null, current: current === null },
    ...days.map((d) => {
      const at = utc(d.date);
      // "Yesterday" only on Today: a settled day's page is cached for a week, and a
      // relative word inside it would name the wrong day by tomorrow.
      const label = d.date === yesterday && current === null ? "Yesterday" : `${WEEKDAYS[at.getUTCDay()]} ${at.getUTCDate()} ${SHORT_MONTHS[at.getUTCMonth()]}`;
      return { date: d.date, label, href: d.read ? `/feed/${d.date}` : null, read: d.read, count: d.read ? d.multi_outlet : null, current: d.date === current };
    }),
  ];
  const at = Math.max(0, all.findIndex((d) => d.current));
  const start = Math.max(0, Math.min(at - 3, all.length - size));
  return all.slice(start, start + size);
}

/** The months from the first day read to today, newest first, as yyyy-mm. */
export function archiveMonths(firstDay: string, today: string): string[] {
  const out: string[] = [];
  for (let m = today.slice(0, 7); m >= firstDay.slice(0, 7); m = plusDays(`${m}-01`, -1).slice(0, 7)) out.push(m);
  return out;
}

export type CalendarDay = { date: string; day: number; kind: "today" | "read" | "unread" | "outside"; reading: ArchiveReading | null };

/**
 * One month of the archive as weeks of seven, Monday first, a blank (null)
 * before the 1st and after the last. A day in the archive's range the API did
 * not list is "unread": never assumed read, never counted.
 */
export function monthGrid(month: string, byDate: Map<string, ArchiveReading>, today: string, firstDay: string): (CalendarDay | null)[][] {
  const first = utc(`${month}-01`);
  const length = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0)).getUTCDate();
  const cells: (CalendarDay | null)[] = Array((first.getUTCDay() + 6) % 7).fill(null);
  for (let d = 1; d <= length; d++) {
    const date = `${month}-${String(d).padStart(2, "0")}`;
    const reading = byDate.get(date) ?? null;
    const kind = date === today ? "today" : date > today || date < firstDay ? "outside" : reading?.read ? "read" : "unread";
    cells.push({ date, day: d, kind, reading });
  }
  while (cells.length % 7) cells.push(null);
  return Array.from({ length: cells.length / 7 }, (_, w) => cells.slice(w * 7, w * 7 + 7));
}
