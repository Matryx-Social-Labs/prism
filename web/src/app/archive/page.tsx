import type { Metadata } from "next";
import Link from "next/link";
import { MetaLine, PageTitle } from "@/components/reading/parts";
import { ArchiveCalendar } from "@/components/ArchiveCalendar";
import { Alert, BackBar } from "@/components/ui";
import { fetchArchive } from "@/lib/api";
import { longDay } from "@/lib/archive";
import { breadcrumbLd, collectionPageLd, jsonLd, social } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// Every day Prism read, as months of days, newest first (audit 02, P1-2): one
// address per day, /feed/<date>. A day it was not reading is hatched — no
// link, no count, never a 0. A day under the floor stays linked, not followed.
export const revalidate = 3600;

const title = "The archive: every day's record";
const description = "The record for every day Prism has read Indian news: the stories reported by two or more monitored outlets, counted per day, and the days Prism was not reading, said so.";
export const metadata: Metadata = {
  title,
  description,
  alternates: { canonical: "/archive" },
  ...social(title, description, "/archive"),
};

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
          <ArchiveCalendar days={days} firstDay={index.first_day ?? index.today} today={index.today} />
        )}
      </div>
    </>
  );
}
