import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { MetaLine, PageTitle, RailHead, ReadingColumns } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { BackBar, EmptyState } from "@/components/ui";
import { fetchFeed, fetchStateHub, type FeedItem, type StateHubPage } from "@/lib/api";
import { entityRel } from "@/lib/entities";
import { languageList } from "@/lib/languages";
import { STATE_HUBS, stateBySlug, type StateHub } from "@/lib/regions";
import { navItem } from "@/lib/sectors";
import { NOT_INDEXED, breadcrumbLd, collectionPageLd, feedListItems, jsonLd, robotsUnless, social } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// A state's or union territory's hub (audit 02, P1-1): the records placed in
// it, counted over 30 days, with the outlets that have a desk there printed as
// the denominator — Karnataka's volume is its desks, not a claim about its
// news. Counts only; states are never ranked. The 33 are known, so they are
// prerendered and refreshed every ten minutes (a few hundred writes a day at
// worst, and none while nothing changes: times print absolutely, lib/Ago).
export const revalidate = 600;

export function generateStaticParams() {
  return STATE_HUBS.map((s) => ({ slug: s.slug }));
}

/** One-source rows shown under their own dashed head, newest first. */
const SINGLE_ROWS = 20;

/** Null when the API cannot answer: the page then says "Not counted yet", never 0. */
const load = (hub: StateHub) => fetchStateHub(hub.code, revalidate).catch(() => null);

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const hub = stateBySlug(slug);
  if (!hub) return { title: "Not found", robots: NOT_INDEXED };
  const counts = await load(hub);
  // No numbers in the title, so it does not churn with the counts.
  const title = `${hub.name} news: one record per story`;
  const langs = counts?.languages.length ? `, in ${languageList(counts.languages)}` : "";
  const description = `Stories placed in ${hub.name} from monitored Indian outlets${langs}: who reported each, who said what.`;
  const path = `/state/${hub.slug}`;
  return {
    title,
    description,
    alternates: { canonical: path },
    ...social(title, description, path),
    // Under the floor, or not counted: readable and linked, not offered to the index.
    ...(counts ? robotsUnless(counts.indexable) : { robots: NOT_INDEXED }),
  };
}

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** Where the volume comes from: the outlets with a desk in the state, linked to the full list. */
function Desks({ hub, counts }: { hub: StateHub; counts: StateHubPage }) {
  const style = { font: "var(--t-body-s)", color: "var(--ink-2)" } as const;
  if (counts.desks.length === 0) {
    return (
      <p style={style}>
        <Link href="/sources" className="p-link">No outlet Prism reads has a desk in {hub.name} yet</Link>; its records come from national and other outlets.
      </p>
    );
  }
  return (
    <p style={style}>
      <Link href="/sources" className="p-link">{count(counts.desks.length, "outlet", "outlets")} with a desk in {hub.name}</Link>: {counts.desks.map((d) => d.name).join(" · ")}.
    </p>
  );
}

export default async function StateHubRoute({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const hub = stateBySlug(slug);
  if (!hub) notFound();
  const [counts, rows] = await Promise.all([
    load(hub),
    fetchFeed({ scope: "region", state: hub.code, sort: "latest", limit: 100 }, revalidate).catch(() => null as FeedItem[] | null),
  ]);
  const url = `${SITE_URL}/state/${hub.slug}`;
  const multi = counts?.items ?? [];
  const singles = (rows ?? []).filter((r) => r.indexable === false);
  const title = `${hub.name} news: one record per story`;

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLd(
            collectionPageLd({
              url,
              name: title,
              description: `Stories placed in ${hub.name} from monitored Indian outlets.`,
              about: {
                "@type": "AdministrativeArea",
                "@id": `${url}#entity`,
                name: hub.name,
                identifier: hub.code,
                ...(counts?.qid ? { sameAs: [`https://www.wikidata.org/wiki/${counts.qid}`] } : {}),
              },
              items: feedListItems(multi),
            }),
          ),
        }}
      />
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLd(breadcrumbLd([{ name: "Prism", url: `${SITE_URL}/` }, { name: "States", url: `${SITE_URL}/state` }, { name: hub.name, url }])),
        }}
      />
      <div className="contents lg:hidden">
        <BackBar label="States" href="/state" />
      </div>
      <ReadingColumns
        railLabel={`Quoted in ${hub.name} records`}
        rail={
          counts && counts.speakers.length > 0 ? (
            <section aria-labelledby="quoted-here">
              <RailHead id="quoted-here">Quoted in {hub.name} records</RailHead>
              <ul className="grid">
                {counts.speakers.map((s) => (
                  <li key={s.slug} className="flex items-baseline justify-between gap-3 border-b py-2.5" style={{ borderColor: "var(--line)" }}>
                    <Link href={`/entity/${s.slug}`} rel={entityRel(s)} className="p-link">{s.name}</Link>
                    <span className="p-meta__prov">{count(s.records, "record", "records")}</span>
                  </li>
                ))}
              </ul>
              <p className="mt-2" style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>
                Word for word, in the newest {counts.speakers_window} records from two or more outlets.
              </p>
            </section>
          ) : undefined
        }
        main={
          <>
            <nav aria-label="Breadcrumb">
              <ol className="flex flex-wrap items-center gap-1.5" style={{ font: "500 13.5px/1.3 var(--font-read)", color: "var(--ink-3)" }}>
                <li className="flex items-center gap-1.5"><Link href="/state" className="p-link">States</Link><span aria-hidden="true">›</span></li>
                <li aria-current="page">{hub.name}</li>
              </ol>
            </nav>
            <header className="grid gap-2.5">
              <p className="p-eyebrow">{hub.kind}</p>
              <PageTitle>{hub.name}</PageTitle>
              {counts ? (
                <>
                  <MetaLine items={[`${count(counts.multi_outlet, "record", "records")} from two or more outlets`, `last ${counts.window_days} days`, `${counts.records} placed here in all`]} />
                  {counts.languages.length > 0 && (
                    <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>Reports in {languageList(counts.languages)}.</p>
                  )}
                  <Desks hub={hub} counts={counts} />
                </>
              ) : (
                <MetaLine items={["— records from two or more outlets", "Not counted yet"]} />
              )}
            </header>
            {counts && counts.subjects.length > 0 && (
              <nav aria-label={`Subjects in ${hub.name}`} className="flex flex-wrap gap-1.5">
                {counts.subjects.map((s) => {
                  const item = navItem(s.root);
                  return item ? (
                    <Link key={s.root} href={item.href} className="p-chip">
                      {item.name} <span className="p-meta__prov">{s.count}</span>
                    </Link>
                  ) : null;
                })}
              </nav>
            )}
            <section aria-labelledby="state-multi" className="grid grid-cols-[minmax(0,1fr)] gap-3">
              <SectionHead
                id="state-multi"
                title="Reported by two or more outlets"
                count={counts ? multi.length : undefined}
                sub={counts && counts.multi_outlet > multi.length ? `the newest ${multi.length} of ${counts.multi_outlet} · most outlets first` : multi.length > 1 ? "most outlets first" : undefined}
              />
              {!counts ? (
                <EmptyState title={`${hub.name}'s records could not load`}>Not counted yet. Try again in a minute.</EmptyState>
              ) : multi.length === 0 ? (
                <EmptyState title={`No record placed in ${hub.name} is from two or more outlets in the last ${counts.window_days} days`} />
              ) : (
                <ol className="p-print grid grid-cols-[minmax(0,1fr)] gap-3">
                  {multi.map((item) => (
                    <ChartRow key={item.id} item={item} />
                  ))}
                </ol>
              )}
            </section>
            {singles.length > 0 && (
              // Line form: one source is dashed, the head's rule included (DESIGN.md § Shape, rules and state).
              <section aria-labelledby="state-single" className="grid grid-cols-[minmax(0,1fr)] gap-3 [&_.p-sechead]:[border-top-style:dashed]">
                <SectionHead
                  id="state-single"
                  title="One source so far"
                  count={Math.min(singles.length, SINGLE_ROWS)}
                  sub={singles.length > SINGLE_ROWS ? `the newest ${SINGLE_ROWS} of ${singles.length} in the latest ${rows?.length ?? 0} placed here` : undefined}
                />
                <ol className="p-print grid grid-cols-[minmax(0,1fr)] gap-3">
                  {singles.slice(0, SINGLE_ROWS).map((item) => (
                    <ChartRow key={item.id} item={item} />
                  ))}
                </ol>
              </section>
            )}
          </>
        }
      />
    </>
  );
}
