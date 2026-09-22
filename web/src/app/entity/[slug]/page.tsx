import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
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

export default async function EntityHubPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const page = await load(slug);
  if (!page) notFound();
  const { entity, record_count, records } = page;
  const url = `${SITE_URL}/entity/${entity.slug}`;

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(entityLd(entity, url, record_count)) }} />
      {records.length > 0 && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLd(itemListLd(`${entity.name} — every record`, url, feedListItems(records))) }}
        />
      )}
      <main className="mx-auto w-full max-w-[860px] px-4 pb-20 pt-6">
        <header className="border-t pt-3" style={{ borderColor: "var(--rule)" }}>
          <p className="font-mono text-[11px] uppercase tracking-[0.08em]" style={{ color: "var(--ink-3)" }}>
            {entity.entity_type.split("|")[0]} · {record_count} {record_count === 1 ? "record" : "records"}
          </p>
          <h1 className="font-display mt-1 text-[34px] leading-[1.08]">{entity.name}</h1>
          {entity.aliases.length > 0 && (
            <p className="mt-1 text-[13px]" style={{ color: "var(--ink-3)" }}>Also written {entity.aliases.slice(0, 4).join(" · ")}</p>
          )}
        </header>
        {records.length === 0 ? (
          <p className="mt-6 text-[15px]" style={{ color: "var(--ink-2)" }}>No records name this actor yet.</p>
        ) : (
          <div className="mt-4">
            {records.map((item, i) => (
              <ChartRow key={item.id} item={item} lead={i === 0} />
            ))}
          </div>
        )}
      </main>
    </>
  );
}
