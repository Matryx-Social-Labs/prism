import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChartRow } from "@/components/ChartRow";
import { DevelopingRail, MetaLine, PageTitle, ReadingColumns } from "@/components/reading/parts";
import { SectionHead } from "@/components/SectionHead";
import { SectorStrip } from "@/components/SectorStrip";
import { TickerChip } from "@/components/tabs/Markets";
import { BackBar, EmptyState } from "@/components/ui";
import { fetchSubject, fetchSubjects, fetchTrending, type SubjectPage as SubjectPayload } from "@/lib/api";
import { sectorGroup, sectorParam } from "@/lib/sectors";
import { breadcrumbLd, feedListItems, itemListLd, jsonLd } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// A node of the subject tree and the stories under it — under IT, so
// /subject/civic/crime holds the violent, the property and the ones we could
// not split. Every node is a URL and a feed or it should not exist
// (common/subjects.py); this is the half that makes that true.
export const revalidate = 120;

async function load(path: string[]): Promise<SubjectPayload | null> {
  try {
    return await fetchSubject(path.join("/"));
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ path: string[] }> }): Promise<Metadata> {
  const { path } = await params;
  const page = await load(path);
  if (!page) return { title: "Not found", robots: { index: false, follow: true } };
  const { node, ancestors, story_count } = page;
  const trail = [...ancestors.map((a) => a.label), node.label].join(" · ");
  return {
    title: `${node.label} — today's record`,
    description: `${story_count} ${story_count === 1 ? "story" : "stories"} in ${trail}, from monitored Indian and international outlets, one record per story: who reported it, what changed, who said what.`,
    alternates: { canonical: `/subject/${node.path.split(".").join("/")}` },
    // A node nobody has reached yet is not a page worth indexing. It stays
    // readable, and comes back when the corpus fills it.
    robots: story_count > 0 ? undefined : { index: false, follow: true },
  };
}

/** Best effort: the rail and the 30-day count never hold the page up. */
async function soft<T>(p: Promise<T>): Promise<T | null> {
  try {
    return await p;
  } catch {
    return null;
  }
}

export default async function SubjectPageRoute({ params }: { params: Promise<{ path: string[] }> }) {
  const { path } = await params;
  const page = await load(path);
  if (!page) notFound();
  const { node, ancestors, children, story_count, stories } = page;
  const href = (p: string) => `/subject/${p.split(".").join("/")}`;
  const url = `${SITE_URL}${href(node.path)}`;
  const root = ancestors[0] ?? node;
  // A subject root that is one of the six sector groups has a story list to
  // draw "Developing" from; Education and Civic have none, so no rail.
  const group = sectorGroup(root.slug);
  const [tree, developing] = await Promise.all([
    soft(fetchSubjects()),
    group ? soft(fetchTrending({ sector: sectorParam(group), limit: 3 })) : Promise.resolve(null),
  ]);
  // The tree counts the live window (30 days); the page counts the archive. Both are printed, each named.
  const live = tree?.nodes.find((n) => n.path === node.path)?.story_count ?? null;
  // The companies the listed reports name — the markets lens's tickers, on Business & Markets only.
  const tickers = root.slug === "business" ? [...new Set(stories.flatMap((s) => s.tickers ?? []))].slice(0, 12) : [];
  const withTickers = stories.filter((s) => (s.tickers ?? []).length > 0).length;
  const parent = ancestors[ancestors.length - 1];

  return (
    <>
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: jsonLd(
            breadcrumbLd([
              { name: "Prism", url: `${SITE_URL}/` },
              ...ancestors.map((a) => ({ name: a.label, url: `${SITE_URL}${href(a.path)}` })),
              { name: node.label, url },
            ]),
          ),
        }}
      />
      {stories.length > 0 && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: jsonLd(itemListLd(`${node.label} — today's record`, url, feedListItems(stories))) }}
        />
      )}
      {/* Claude Design · ReadingB Subject: the subject rail on the left, the node's
          stories in the 640 column, what is developing in its subject on the right. */}
      <div className="contents lg:hidden">
        <BackBar label="Today" href="/feed" />
      </div>
      <ReadingColumns
        left={<SectorStrip active={root.slug} responsiveRail />}
        railLabel="Developing in this subject"
        rail={developing && developing.length > 0 ? <DevelopingRail stories={developing} title={ancestors.length ? `Developing in ${root.label}` : "Developing here"} /> : undefined}
        main={
          <>
            <header className="grid gap-2.5">
              {ancestors.length > 0 && (
                <nav aria-label="Breadcrumb">
                  <ol className="flex flex-wrap items-center gap-1.5" style={{ font: "500 13.5px/1.3 var(--font-read)", color: "var(--ink-3)" }}>
                    {ancestors.map((a) => (
                      <li key={a.path} className="flex items-center gap-1.5">
                        <Link href={href(a.path)} className="p-link">{a.label}</Link>
                        <span aria-hidden="true">›</span>
                      </li>
                    ))}
                    <li aria-current="page">{node.label}</li>
                  </ol>
                </nav>
              )}
              <PageTitle>{node.label}</PageTitle>
              <MetaLine items={[`${story_count} ${story_count === 1 ? "story" : "stories"}`, live != null ? `30 days: ${live}` : null, stories.length > 1 ? "newest first" : null]} />
            </header>
            {children.length > 0 && (
              <nav aria-label="Sub-topics" className="p-hide-scroll -mx-[var(--gutter)] flex gap-1.5 overflow-x-auto px-[var(--gutter)] lg:mx-0 lg:flex-wrap lg:px-0">
                <Link href={href(node.path)} className="p-chip" aria-current="page">All</Link>
                {children.map((c) => (
                  <Link key={c.path} href={href(c.path)} className="p-chip">{c.label}</Link>
                ))}
              </nav>
            )}
            {tickers.length > 0 && (
              <section aria-labelledby="companies-named" className="grid gap-2">
                <SectionHead id="companies-named" title="Companies named" sub={`in ${withTickers} of the ${stories.length} stories below`} />
                <ul className="flex flex-wrap gap-2">
                  {tickers.map((t) => <li key={t}><TickerChip symbol={t} /></li>)}
                </ul>
              </section>
            )}
            <section aria-label={`${node.label} stories`}>
              {stories.length === 0 ? (
                <EmptyState
                  title={`No stories in ${node.label} yet`}
                  action={parent ? <Link href={href(parent.path)} className="p-link" style={{ font: "600 14.5px/1.3 var(--font-read)" }}>All of {parent.label} →</Link> : undefined}
                />
              ) : (
                <ol className="p-print grid grid-cols-[minmax(0,1fr)] gap-3">
                  {stories.map((item) => (
                    <ChartRow key={item.id} item={item} pageCode={group?.code ?? null} />
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
