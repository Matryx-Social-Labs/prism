import type { Metadata } from "next";
import Link from "next/link";
import { notFound, redirect } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { MetaLine, PageTitle, ReadingColumns, SubjectTrail } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { BackBar, EmptyState } from "@/components/ui";
import { fetchArchiveDay, type ArchiveDay } from "@/lib/api";
import { bySubject, dayRevalidate, istToday, longDay, parseDay } from "@/lib/archive";
import { istTime } from "@/lib/dateline";
import { NOT_INDEXED, breadcrumbLd, collectionPageLd, feedListItems, jsonLd, robotsUnless, social } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// One IST day's record (audit 02, P1-2): the records Prism first saw that day
// from two or more outlets, by subject, most outlets first; the rest counted,
// not listed. A day Prism did not read says so and counts nothing. Under /feed
// so the Today tab holds it; today's own date is /feed itself.
//
// Rendered on first request and kept: an hour while the day is young, a week
// once it has settled (lib/archive.dayRevalidate sets the fetch's clock, which
// is the page's). Every time prints absolutely, so a re-render writes nothing new.
export const revalidate = 604800;
export const dynamicParams = true;
export function generateStaticParams() {
  return [];
}

type Params = { params: Promise<{ date: string }> };

/** Null for a date the archive does not hold (404); throws when the API cannot answer, never guesses. */
const load = (date: string) => fetchArchiveDay(date, dayRevalidate(date));

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const date = parseDay((await params).date);
  if (!date || date === istToday()) return { title: "Not found", robots: NOT_INDEXED };
  const day = await load(date).catch(() => null);
  if (!day) return { title: "Not found", robots: NOT_INDEXED };
  const long = longDay(date);
  const title = `India news on ${long} — the record`;
  const description = day.read
    ? `The record for ${long}: ${count(day.multi_outlet ?? 0, "story", "stories")} reported by two or more monitored Indian outlets, by subject, with who said what.`
    : `Prism was not reading on ${long}, so no record was kept for this day.`;
  const path = `/feed/${date}`;
  return { title, description, alternates: { canonical: path }, ...social(title, description, path), ...robotsUnless(day.indexable) };
}

/** What Prism read on the day, when it was not the whole of it, in words; the times are provenance. */
function ReadingNote({ day }: { day: ArchiveDay }) {
  const style = { font: "var(--t-body-s)", color: "var(--ink-2)" } as const;
  if (!day.read) return <p style={style}>Prism was not reading on this day, so nothing on it was counted.</p>;
  if (day.whole_day && day.settled) return null;
  const at = (iso: string | null) => (iso ? <time dateTime={iso} className="font-mono text-[12px]">{istTime(iso)}</time> : "—");
  if (day.settled) {
    return <p style={style}>Prism read from {at(day.read_from)} to {at(day.read_to)} IST on this day, not all of it.</p>;
  }
  const span = day.whole_day ? <>until {at(day.read_to)} IST</> : <>from {at(day.read_from)} to {at(day.read_to)} IST</>;
  return <p style={style}>Prism read {span} on this day and has not read since, so this record is not complete.</p>;
}

export default async function ArchiveDayPage({ params }: Params) {
  const date = parseDay((await params).date);
  if (!date) notFound();
  // Fetched before the redirect so today's cached answer keeps the day's short clock.
  const day = await load(date);
  // Today's record is /feed. Temporary (307), not 308: tomorrow this address is
  // yesterday's page, and a browser keeps a permanent redirect for good.
  if (date === istToday()) redirect("/feed");
  if (!day) notFound();

  const url = `${SITE_URL}/feed/${date}`;
  const long = longDay(date);
  const groups = bySubject(day.items);
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLd(
            collectionPageLd({
              url,
              name: `India news on ${long} — the record`,
              description: day.read ? `Stories first seen on ${long} and reported by two or more monitored Indian outlets.` : `Prism was not reading on ${long}.`,
              temporalCoverage: date,
              items: feedListItems(day.items),
            }),
          ),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLd(breadcrumbLd([{ name: "Prism", url: `${SITE_URL}/` }, { name: "Archive", url: `${SITE_URL}/archive` }, { name: long, url }])),
        }}
      />
      <div className="contents lg:hidden">
        <BackBar label="Archive" href="/archive" />
      </div>
      <ReadingColumns
        main={
          <>
            <SubjectTrail steps={[{ name: "Archive", href: "/archive" }]} />
            <header className="grid gap-2.5">
              <p className="p-eyebrow">The record for</p>
              <PageTitle>{long}</PageTitle>
              {day.read && (
                <MetaLine
                  items={[
                    `${day.multi_outlet ?? 0} from two or more outlets`,
                    `${day.single_source ?? 0} single-source, counted, not listed`,
                    day.languages ? count(day.languages, "language", "languages") : null,
                  ]}
                />
              )}
              <ReadingNote day={day} />
            </header>
            {day.read && day.items.length === 0 && (
              <EmptyState title="No record first seen on this day is from two or more outlets">
                {count(day.single_source ?? 0, "record from one outlet was", "records from one outlet were")} counted; they are not listed.
              </EmptyState>
            )}
            {groups.map((g) => (
              <section key={g.key ?? "unplaced"} aria-labelledby={`day-${g.key ?? "unplaced"}`} className="grid grid-cols-[minmax(0,1fr)] gap-3">
                <SectionHead
                  id={`day-${g.key ?? "unplaced"}`}
                  title={g.name}
                  count={g.items.length}
                  sub={g.items.length > 1 ? "most outlets first" : undefined}
                  right={g.href ? <Link href={g.href} className="p-link whitespace-nowrap text-[13.5px]">All {g.name} →</Link> : undefined}
                />
                <ol className="p-print grid grid-cols-[minmax(0,1fr)] gap-3">
                  {g.items.map((item) => (
                    <ChartRow key={item.id} item={item} />
                  ))}
                </ol>
              </section>
            ))}
            <nav aria-label="Other days" className="flex flex-wrap justify-between gap-3 border-t pt-4" style={{ borderColor: "var(--line)" }}>
              {day.prev ? <Link href={`/feed/${day.prev}`} className="p-link">← {longDay(day.prev)}</Link> : <span />}
              <Link href="/archive" className="p-link">Every day</Link>
              {day.next ? (
                <Link href={`/feed/${day.next}`} className="p-link">{longDay(day.next)} →</Link>
              ) : day.next_is_today ? (
                <Link href="/feed" className="p-link">Today&rsquo;s record →</Link>
              ) : (
                <span />
              )}
            </nav>
          </>
        }
      />
    </>
  );
}
