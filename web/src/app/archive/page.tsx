import type { Metadata } from "next";
import Link from "next/link";
import { MetaLine, PageTitle } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { Alert, BackBar } from "@/components/ui";
import { fetchArchive, type ArchiveReading } from "@/lib/api";
import { archiveRows, longDay } from "@/lib/archive";
import { istTime } from "@/lib/dateline";
import { breadcrumbLd, collectionPageLd, followRel, jsonLd, social } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// Every day Prism read, newest first (audit 02, P1-2): one address per day,
// /feed/<date>. A run of days it was not reading is one line that says so —
// no link, no count, never a 0. A day under the floor stays linked, not followed.
export const revalidate = 3600;

const title = "The archive: every day's record";
const description = "The record for every day Prism has read Indian news: the stories reported by two or more monitored outlets, counted per day, and the days Prism was not reading, said so.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/archive" },
  ...social(title, description, "/archive"),
};

const at = (iso: string | null) => (iso ? <time dateTime={iso} className="font-mono text-[12px]">{istTime(iso)}</time> : "—");

/** A day read in part says which part; a day after which Prism stopped says when. */
function DayNote({ day }: { day: ArchiveReading }) {
  if (day.whole_day && day.settled) return null;
  return (
    <span style={{ font: "400 12.5px/1.4 var(--font-read)", color: "var(--ink-3)" }}>
      {day.settled ? <>read {at(day.read_from)}–{at(day.read_to)} IST</> : <>stopped at {at(day.read_to)} IST, not complete</>}
    </span>
  );
}

function DayRow({ day }: { day: ArchiveReading }) {
  return (
    <li className="flex items-baseline justify-between gap-3 border-b py-2.5" style={{ borderColor: "var(--line)" }}>
      <Link href={`/feed/${day.date}`} rel={followRel(day.indexable)} className="p-link">{longDay(day.date)}</Link>
      <span className="grid justify-items-end text-right">
        <span className="p-meta__prov">{day.multi_outlet ?? 0} from two or more outlets</span>
        <DayNote day={day} />
      </span>
    </li>
  );
}

export default async function ArchiveIndexPage() {
  const index = await fetchArchive(revalidate).catch(() => null);
  const url = `${SITE_URL}/archive`;
  const days = index?.days ?? [];
  const read = days.filter((d) => d.read);
  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLd(collectionPageLd({ url, name: title, description, items: days.filter((d) => d.indexable).map((d) => ({ url: `${SITE_URL}/feed/${d.date}`, name: `India news on ${longDay(d.date)}` })) })),
        }}
      />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(breadcrumbLd([{ name: "Prism", url: `${SITE_URL}/` }, { name: "Archive", url }])) }} />
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <div className="mx-auto grid w-full max-w-[var(--reading)] grid-cols-[minmax(0,1fr)] gap-6 px-[var(--gutter)] pb-16 pt-5 lg:pt-10">
        <header className="grid gap-2">
          <PageTitle>The archive</PageTitle>
          <p className="max-w-[60ch] text-pretty" style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            One page for every day Prism read: the records it first saw that day, from two or more outlets, by subject. A day Prism was not reading says so; nothing on it is counted.
          </p>
          {index?.first_day && <MetaLine items={[`${read.length} ${read.length === 1 ? "day" : "days"} read`, `since ${longDay(index.first_day)}`]} />}
        </header>
        {!index ? (
          <Alert tone="error" title="The archive could not load.">Try again in a minute, or read <Link href="/feed" className="p-link">today&rsquo;s record</Link>.</Alert>
        ) : (
          <section aria-labelledby="archive-days" className="grid gap-1">
            <SectionHead id="archive-days" title="Days" count={read.length} sub="newest first" />
            <ul className="grid">
              <li className="flex items-baseline justify-between gap-3 border-b py-2.5" style={{ borderColor: "var(--line)" }}>
                <Link href="/feed" className="p-link">Today</Link>
                <span style={{ font: "400 13px/1.4 var(--font-read)", color: "var(--ink-3)" }}>the record as it is now</span>
              </li>
              {archiveRows(days).map((r) =>
                r.kind === "day" ? (
                  <DayRow key={r.day.date} day={r.day} />
                ) : (
                  <li key={r.from} className="flex items-baseline justify-between gap-3 border-b border-dashed py-2.5" style={{ borderColor: "var(--line-strong)", color: "var(--ink-3)" }}>
                    <span>{r.from === r.to ? longDay(r.from) : `${longDay(r.from)} – ${longDay(r.to)}`}</span>
                    <span style={{ font: "400 13px/1.4 var(--font-read)" }}>Prism was not reading</span>
                  </li>
                ),
              )}
            </ul>
          </section>
        )}
      </div>
    </>
  );
}
