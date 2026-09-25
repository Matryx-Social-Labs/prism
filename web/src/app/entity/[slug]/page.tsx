import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { MetaLine, PageTitle, ReadingColumns } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { BackBar, EmptyState } from "@/components/ui";
import { fetchEntity, type EntityPage as EntityPayload } from "@/lib/api";
import { entityLd, feedListItems, itemListLd, jsonLd } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// An actor and every record it appears in. The cast of a record was already
// extracted and folded to one identity; until now those names linked at
// `/search`, which is noindex, so the most-linked anchors on the site pointed
// nowhere an engine would keep (audit H29).
//
// A page exists for every actor a chip names — a link that 404s is worse than a
// thin page — but only one in three or more records asks to be indexed. The
// floor is the API's (`INDEXABLE_MIN_RECORDS`) and arrives as `indexable`.
export const revalidate = 300;

async function load(slug: string): Promise<EntityPayload | null> {
  try {
    return await fetchEntity(slug);
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const page = await load(slug);
  if (!page) return { title: "Not found", robots: { index: false, follow: true } };
  const { entity, record_count, indexable } = page;
  return {
    title: `${entity.name} — every record`,
    description: `Every Prism record naming ${entity.name}: ${record_count} ${record_count === 1 ? "story" : "stories"} from monitored Indian and international outlets, each with its reports, what changed and who said what.`,
    alternates: { canonical: `/entity/${entity.slug}` },
    // A stub still resolves for the reader and still passes its links on; it
    // simply does not ask for the crawl budget the records need.
    robots: indexable ? undefined : { index: false, follow: true },
  };
}

/** The eyebrow for the actor's kind — only for the kinds the API maps with confidence ("Thing" says nothing). */
const KIND: Record<string, string> = {
  Person: "Person",
  Organization: "Organisation",
  GovernmentOrganization: "Organisation",
  NewsMediaOrganization: "Organisation",
  Place: "Place",
  Country: "Place",
  Product: "Product",
};

export default async function EntityHubPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = await load(slug);
  if (!page) notFound();
  const { entity, record_count, records } = page;
  const url = `${SITE_URL}/entity/${entity.slug}`;
  const kind = KIND[entity.schema_type];
  const stories = `${record_count} ${record_count === 1 ? "story" : "stories"}`;

  // Claude Design · ReadingB Entity. What the design also draws and the API does
  // not carry is left out, never estimated: a role, a quote count and the
  // Quotes tab, "Named alongside", stories per day, and Follow (the watchlist
  // follows tickers and sectors only).
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(entityLd(entity, url, record_count)) }} />
      {records.length > 0 && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLd(itemListLd(`${entity.name} — every record`, url, feedListItems(records))) }}
        />
      )}
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <ReadingColumns
        main={
          <>
            <header className="grid gap-2.5">
              {kind && <p className="p-eyebrow">{kind}</p>}
              <PageTitle>{entity.name}</PageTitle>
              <MetaLine items={[stories]} />
              {entity.aliases.length > 0 && (
                <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>Also written {entity.aliases.slice(0, 4).join(" · ")}</p>
              )}
            </header>
            <section aria-labelledby="entity-stories" className="grid grid-cols-[minmax(0,1fr)] gap-3">
              <SectionHead
                id="entity-stories"
                title="Stories"
                count={record_count}
                sub={records.length < record_count ? `newest first · the latest ${records.length}` : records.length > 1 ? "newest first" : undefined}
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
            </section>
          </>
        }
      />
    </>
  );
}
