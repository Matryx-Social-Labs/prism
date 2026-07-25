import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { fetchEvent, type EventDetail } from "@/lib/api";
import { StoryView } from "@/components/StoryView";
import { SITE_URL } from "@/lib/site";

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

function metaDescription(event: EventDetail): string {
  const text = event.summary ?? event.lens_briefs?.reader ?? event.title;
  return text.length > 200 ? `${text.slice(0, 197).trimEnd()}…` : text;
}

export async function generateMetadata({ params }: { params: Promise<{ id: string }> }): Promise<Metadata> {
  const { id } = await params;
  const event = await load(id);
  if (!event) return { title: "Story not found" };

  const description = metaDescription(event);
  const url = `/story/${id}`;
  // Only set `images` when the story has a publisher photo. An explicit
  // `images: undefined` still counts as the page defining its own images, which
  // suppresses the opengraph-image.tsx fallback — shipping a share card with no
  // image at all in the common case, since most stories carry no photo.
  const images = event.image_url ? { images: [event.image_url] } : {};
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
      ...images,
      publishedTime: event.occurred_at ?? undefined,
      modifiedTime: event.last_updated_at,
      section: event.sector ?? undefined,
    },
    twitter: {
      // Always large: either the publisher photo or the generated 1200x630 card.
      card: "summary_large_image",
      title: event.title,
      description,
      ...images,
    },
  };
}

export default async function StoryPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const event = await load(id);
  if (!event) notFound();

  // NewsArticle structured data — lets search + social render this as a news
  // result with headline, image, and dates instead of a bare link.
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "NewsArticle",
    headline: event.title,
    description: metaDescription(event),
    ...(event.image_url ? { image: [event.image_url] } : {}),
    datePublished: event.occurred_at ?? event.last_updated_at,
    dateModified: event.last_updated_at,
    url: `${SITE_URL}/story/${id}`,
    articleSection: event.sector ?? undefined,
    author: { "@type": "Organization", name: "Prism" },
    publisher: { "@type": "Organization", name: "Prism" },
  };

  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }} />
      <StoryView event={event} />
    </>
  );
}
