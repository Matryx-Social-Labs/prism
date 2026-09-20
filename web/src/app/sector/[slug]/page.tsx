import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { FrontPage } from "@/components/FrontPage";
import { fetchFeed, type FeedItem } from "@/lib/api";
import { FEED_WINDOW } from "@/lib/feedWindow";
import { SECTOR_GROUPS, sectorGroup, sectorParam } from "@/lib/sectors";
import { feedListItems, itemListLd, jsonLd } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// The chart filtered to one of the reader's six subjects, its code active in
// the strip. Legacy pipeline slugs (/sector/finance) resolve to their group and
// declare the group's address as canonical; an unknown slug is a 404, not a
// second copy of the whole chart. Rendered on the server so the subject's rows
// and its own title are in the HTML.
export const revalidate = 60;

// The six subjects are known: prerender them and refresh on the same clock.
export function generateStaticParams() {
  return SECTOR_GROUPS.map((g) => ({ slug: g.slug }));
}

export async function generateMetadata({ params }: { params: Promise<{ slug: string }> }): Promise<Metadata> {
  const { slug } = await params;
  const group = sectorGroup(slug);
  if (!group) return { title: "Not found" };
  return {
    title: `${group.name} — today's record`,
    description: `Today's ${group.name} stories from monitored Indian and international outlets, one record per story: who reported it, what changed, who said what.`,
    alternates: { canonical: `/sector/${group.slug}` },
  };
}

export default async function SectorPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const group = sectorGroup(slug);
  if (!group) notFound();
  let initial: FeedItem[] | null = null;
  try {
    initial = await fetchFeed({ sector: sectorParam(group), sort: "latest", limit: FEED_WINDOW });
  } catch {
    // API unreachable at render: the client fetches as before.
  }
  return (
    <>
      {initial && initial.length > 0 && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(itemListLd(`${group.name} — today's record`, `${SITE_URL}/sector/${group.slug}`, feedListItems(initial))) }} />
      )}
      <FrontPage sector={slug} initial={initial} />
    </>
  );
}
