import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { fetchEvent, type EventDetail } from "@/lib/api";
import { StoryView } from "@/components/StoryView";
import { eventDescription, jsonLd, newsArticleLd } from "@/lib/seo";

export const dynamic = "force-dynamic";

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
  const url = `/story/${id}`;
  // The share card is always Prism's own (opengraph-image.tsx): a publisher's
  // photograph is never presented as our card (legal review, 2026-09-18).
  return {
    title: event.title,
    description,
    alternates: { canonical: url },
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

  // NewsArticle structured data (lib/seo): headline, dates, the reports it is
  // based on and the entities it is about — so search and answer engines see
  // a grounded record, not a bare link. No image: the publisher's photograph
  // is not ours to declare.
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(newsArticleLd(event)) }} />
      <StoryView event={event} />
    </>
  );
}
