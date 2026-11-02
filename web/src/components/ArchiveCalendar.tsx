import Link from "next/link";
import { SectionHead } from "@/components/SectionHead";
import type { ArchiveReading } from "@/lib/api";
import { archiveMonths, longDay, monthGrid, type CalendarDay } from "@/lib/archive";
import { LONG_MONTHS } from "@/lib/dateline";
import { followRel } from "@/lib/seo";

const WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

/** One day: linked with its count when read, hatched when Prism was not reading, a bare number outside the archive. */
function Day({ c }: { c: CalendarDay }) {
  if (c.kind === "today") {
    return (
      <Link href="/feed" className="sc-cal__day sc-cal__day--read sc-cal__day--today" aria-current="date" aria-label={`${longDay(c.date)}, today's record`}>
        <span>{c.day}</span>
        <span className="p-count">today</span>
      </Link>
    );
  }
  if (c.kind === "read" && c.reading) {
    const n = c.reading.multi_outlet ?? 0;
    // Read in part, or stopped before the day ended: dashed, the system's provisional;
    // the day's own page says which hours.
    const part = !c.reading.settled ? ", not complete" : !c.reading.whole_day ? ", read in part" : "";
    return (
      <Link
        href={`/feed/${c.date}`}
        rel={followRel(c.reading.indexable)}
        prefetch={false}
        className={`sc-cal__day sc-cal__day--read${part ? " sc-cal__day--part" : ""}`}
        aria-label={`${longDay(c.date)}, ${n} ${n === 1 ? "record" : "records"} from two or more outlets${part}`}
      >
        <span>{c.day}</span>
        <span className="p-count">{n}</span>
      </Link>
    );
  }
  if (c.kind === "unread") {
    return (
      <span className="sc-cal__day sc-cal__day--off" title="Prism was not reading this day">
        <span>{c.day}</span>
        <span className="sr-only">, Prism was not reading</span>
      </span>
    );
  }
  return <span className="sc-cal__day" aria-hidden="true">{c.day}</span>;
}

/**
 * The archive as months of days (Instagram's archive calendar, Mobbin), newest
 * month first. Every read day is a link, so the calendar is as crawlable as the
 * list it replaces; a day not read is hatched, the system's "not counted".
 */
export function ArchiveCalendar({ days, firstDay, today }: { days: ArchiveReading[]; firstDay: string; today: string }) {
  const byDate = new Map(days.map((d) => [d.date, d]));
  return (
    <div className="grid gap-8">
      {archiveMonths(firstDay, today).map((month) => {
        const [y, m] = month.split("-").map(Number);
        const read = days.filter((d) => d.read && d.date.startsWith(month)).length + (today.startsWith(month) ? 1 : 0);
        const id = `month-${month}`;
        return (
          <section key={month} aria-labelledby={id} className="grid gap-2">
            <SectionHead id={id} title={`${LONG_MONTHS[m - 1]} ${y}`} count={read} sub={`${read === 1 ? "day" : "days"} read · records from two or more outlets`} />
            <div role="table" aria-label={`${LONG_MONTHS[m - 1]} ${y}`} className="sc-cal">
              <div role="row" className="sc-cal__week">
                {WEEK.map((w) => (
                  <span key={w} role="columnheader" className="sc-cal__head">{w}</span>
                ))}
              </div>
              {monthGrid(month, byDate, today, firstDay).map((week, i) => (
                <div role="row" key={i} className="sc-cal__week">
                  {week.map((c, j) => (
                    <span role="cell" key={j}>{c && <Day c={c} />}</span>
                  ))}
                </div>
              ))}
            </div>
          </section>
        );
      })}
    </div>
  );
}
