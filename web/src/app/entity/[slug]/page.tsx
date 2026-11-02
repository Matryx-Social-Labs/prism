import type { Metadata } from "next";
import Link from "next/link";
import { notFound, permanentRedirect } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { EntityQuotes } from "@/components/reading/EntityQuotes";
import { MetaLine, PageTitle, ReadingColumns } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { BackBar, EmptyState } from "@/components/ui";
import { ENTITY_PAGE, fetchEntity, type EntityPage as EntityPayload } from "@/lib/api";
import { SCHEMA_KIND } from "@/lib/entities";
import { stateBySlug } from "@/lib/regions";
import { breadcrumbLd, entityLd, jsonLd, quotationsLd, robotsUnless, social } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// An actor and every record it appears in. The cast of a record was already
// extracted and folded to one identity; until now those names linked at
// `/search`, which is noindex, so the most-linked anchors on the site pointed
// nowhere an engine would keep (audit H29).
//
// A page exists for every actor a chip names — a link that 404s is worse than a
// thin page — but only one in four or more records asks to be indexed. The
// floor is the API's (`INDEXABLE_MIN_RECORDS`) and arrives as `indexable`.
export const revalidate = 300;

// null only for a page that does not exist; an outage throws (a 5xx, not a 404).
const load = (slug: string, page: number): Promise<EntityPayload | null> => fetchEntity(slug, page);

type Params = { params: Promise<{ slug: string }>; searchParams?: Promise<{ page?: string }> };

/** ?page=N, a whole number from 1; anything else reads as the first page. */
const pageOf = async (searchParams: Params["searchParams"]) => {
  const n = Number((await searchParams)?.page);
  return Number.isInteger(n) && n > 1 ? n : 1;
};
const pageHref = (slug: string, n: number) => (n > 1 ? `/entity/${slug}?page=${n}` : `/entity/${slug}`);

/**
 * A state's own name has one page, its hub: /entity/karnataka and
 * /state/karnataka competed for "Karnataka news" (audit 02, P1-1), so the
 * actor address 308s there before anything is fetched, and the entities
 * sitemap leaves it out (api/routes/entity.sitemap_entities).
 */
function deferToStateHub(slug: string): void {
  const hub = stateBySlug(slug);
  if (hub) permanentRedirect(`/state/${hub.slug}`);
}

export async function generateMetadata({ params, searchParams }: Params): Promise<Metadata> {
  const { slug } = await params;
  deferToStateHub(slug);
  const n = await pageOf(searchParams);
  const page = await load(slug, n);
  if (!page) return { title: "Not found", robots: { index: false, follow: true } };
  const { entity, record_count, indexable } = page;
  const said = (page.quotes?.length ?? 0) >= SAID_IN_TITLE;
  const base = said ? `${entity.name} — what was said, and every record` : `${entity.name} — every record`;
  const title = n > 1 ? `${base}, page ${n}` : base;
  const description = said
    ? saidDescription(entity.name, page.quote_count ?? 0, page.reported_count ?? 0, page.quoted_records ?? 0)
    : `Every Prism record naming ${entity.name}: ${record_count} ${record_count === 1 ? "story" : "stories"} from monitored Indian outlets, each with its reports, what changed and who said what.`;
  return {
    title,
    description,
    // Each page of older records is its own address, never folded into page one.
    alternates: { canonical: pageHref(entity.slug, n) },
    ...social(title, description, pageHref(entity.slug, n)),
    // A stub still resolves for the reader and still passes its links on; it
    // simply does not ask for the crawl budget the records need.
    ...robotsUnless(indexable),
  };
}

/** From this many shown quotes the title and description lead with what was said (P0-3). */
const SAID_IN_TITLE = 3;

const count = (n: number, one: string, many: string) => `${n} ${n === 1 ? one : many}`;

/** The meta description once the page carries quotes: quotes and reported speech counted apart, as the page prints them. */
function saidDescription(name: string, quotes: number, reported: number, records: number): string {
  const where = `in ${count(records, "Prism record", "Prism records")}, with every outlet that reported them.`;
  if (quotes === 0) return `${count(reported, "statement", "statements")} by ${name} as the articles report them, checked against the article, ${where}`;
  const said = `${count(quotes, "quote", "quotes")} from ${name}, word for word`;
  return reported
    ? `${said}, and ${count(reported, "reported statement", "reported statements")}, all checked against the article, ${where}`
    : `${said} and checked against the article, ${where}`;
}

export default async function EntityHubPage({ params, searchParams }: Params) {
  const { slug } = await params;
  deferToStateHub(slug);
  const n = await pageOf(searchParams);
  const page = await load(slug, n);
  if (!page || (n > 1 && page.records.length === 0)) notFound();
  const { entity, record_count, records } = page;
  const url = `${SITE_URL}/entity/${entity.slug}`;
  const kind = SCHEMA_KIND[entity.schema_type];
  const stories = `${record_count} ${record_count === 1 ? "story" : "stories"}`;
  const quoteCount = page.quote_count ?? 0;
  const reportedCount = page.reported_count ?? 0;
  const quotesLd = quotationsLd(page.quotes ?? [], url);

  // Claude Design · ReadingB Entity. The role, the quote count and the quotes
  // (a section here, not the design's tab) come from the API; what the design
  // also draws and the API does not carry is left out, never estimated:
  // "Named alongside", stories per day, and Follow (the watchlist follows
  // tickers and sectors only).
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(entityLd(entity, url, record_count, records, quotesLd)) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(breadcrumbLd([{ name: "Prism", url: `${SITE_URL}/` }, { name: entity.name, url }])) }} />
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <ReadingColumns
        main={
          <>
            <header className="grid gap-2.5">
              {kind && <p className="p-eyebrow">{kind}</p>}
              <PageTitle>{entity.name}</PageTitle>
              {/* Who they are, as the articles put it — never a title we supplied. */}
              {page.role && <p style={{ font: "var(--t-body-s)", color: "var(--ink-2)" }}>As the articles put it: {page.role}</p>}
              <MetaLine items={[quoteCount > 0 && count(quoteCount, "quote", "quotes"), reportedCount > 0 && `${reportedCount} reported`, stories]} />
              {entity.aliases.length > 0 && (
                <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>Also written {entity.aliases.slice(0, 4).join(" · ")}</p>
              )}
            </header>
            <section aria-labelledby="entity-stories" className="grid grid-cols-[minmax(0,1fr)] gap-3">
              <SectionHead
                id="entity-stories"
                title="Stories"
                count={record_count}
                sub={n > 1 ? `newest first · page ${n} of ${Math.ceil(record_count / ENTITY_PAGE)}` : records.length < record_count ? `newest first · the latest ${records.length}` : records.length > 1 ? "newest first" : undefined}
              />
              {records.length === 0 ? (
                <EmptyState title="No stories name this actor yet">A story joins this page when a report on it names {entity.name}.</EmptyState>
              ) : (
                <ol className="p-print grid grid-cols-[minmax(0,1fr)] gap-3">
                  {records.map((item) => (
                    <ChartRow key={item.id} item={item} />
                  ))}
                </ol>
              )}
              {(n > 1 || n * ENTITY_PAGE < record_count) && (
                <nav aria-label="More records" className="flex flex-wrap justify-between gap-3 pt-2">
                  {n > 1 ? <Link href={pageHref(entity.slug, n - 1)} className="p-link">← Newer records</Link> : <span />}
                  {n * ENTITY_PAGE < record_count && <Link href={pageHref(entity.slug, n + 1)} className="p-link">Older records →</Link>}
                </nav>
              )}
            </section>
            {/* The quotes are read from the newest records: page one only, never repeated. */}
            {n === 1 && <EntityQuotes page={page} />}
          </>
        }
      />
    </>
  );
}
