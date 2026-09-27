import type { Metadata } from "next";
import { notFound, permanentRedirect } from "next/navigation";
import { fetchEvent, type EventDetail } from "@/lib/api";
import { StoryView } from "@/components/StoryView";
import { sectorGroup } from "@/lib/sectors";
import { breadcrumbLd, eventDescription, jsonLd, newsArticleLd, robotsUnless } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// Rendered once a minute, not per request: nothing server-rendered here varies
// by reader (the lens unlock is client-side), so a crawler hitting thousands of
// records and a reader opening one share the cached shell (audit: force-dynamic
// dated from the scaffold and cost a Railway round trip per view).
export const revalidate = 60;

// Next memoizes native fetch per request, so generateMetadata and the page
// share one call to fetchEvent.
async function load(id: string): Promise<EventDetail | null> {
  try {
    return await fetchEvent(id);
  } catch {
    return null;
  }
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const event = await load(id);
  if (!event) return { title: "Story not found" };

  const description = eventDescription(event);
  // event.id, not the requested id: a merged record's old address answers with
  // the survivor, and its canonical must name the survivor (the redirect below
  // reaches a crawler as a streamed meta refresh, not an HTTP 308).
  const url = `/story/${event.id}`;
  // The share card is always Prism's own (opengraph-image.tsx): a publisher's
  // photograph is never presented as our card (legal review, 2026-09-18).
  return {
    title: event.title,
    description,
    alternates: { canonical: url },
    // One outlet: a rewrite Google already has from that outlet (common/outlets.record_indexable).
    ...robotsUnless(event.indexable !== false),
    openGraph: {
      type: "article",
      siteName: "Prism",
      title: event.title,
      description,
      url,
      publishedTime: event.occurred_at ?? undefined,
      modifiedTime: event.last_updated_at,
      section: event.sector ?? undefined,
    },
    twitter: {
      // Always large: either the publisher photo or the generated 1200x630 card.
      card: "summary_large_image",
      title: event.title,
      description,
    },
  };
}

export default async function StoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const event = await load(id);
  if (!event) notFound();
  // A record merged into the one it duplicated: the API's 308 was followed, so
  // this is the survivor. Its address is the one to share and index.
  if (event.id !== id) permanentRedirect(`/story/${event.id}`);

  // NewsArticle structured data (lib/seo): headline, dates, the reports it is
  // based on and the entities it is about — so search and answer engines see
  // a grounded record, not a bare link. The image is the record's own card.
  const group = sectorGroup(event.sector);
  const trail = [
    { name: "Prism", url: `${SITE_URL}/` },
    ...(group ? [{ name: group.name, url: `${SITE_URL}/sector/${group.slug}` }] : []),
    { name: event.title, url: `${SITE_URL}/story/${event.id}` },
  ];
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(newsArticleLd(event)) }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(breadcrumbLd(trail)) }} />
      <StoryView event={event} />
    </>
  );
}
