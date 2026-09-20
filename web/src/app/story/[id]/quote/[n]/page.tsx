import type { Metadata } from "next";
import { notFound } from "next/navigation";
import StoryPage from "../../page";
import { fetchEvent } from "@/lib/api";
import { findQuote } from "@/lib/quotes";

// One quote's own address: the same record page, with the quote as the
// shared preview (opengraph-image.tsx beside this file draws the quote card).
// Canonical stays the record, so search does not see a second copy.
export async function generateMetadata({ params }: { params: Promise<{ id: string; n: string }> }): Promise<Metadata> {
  const { id, n } = await params;
  let event;
  try {
    event = await fetchEvent(id);
  } catch {
    return { title: "Story not found" };
  }
  const q = findQuote(event.claims, n);
  if (!q) return { title: event.title };
  const title = `“${q.claim.quote_text.length > 90 ? `${q.claim.quote_text.slice(0, 89)}…` : q.claim.quote_text}” — ${q.speaker}`;
  const description = `${q.speaker}${q.role ? `, ${q.role}` : ""}, as reported by ${q.claim.source_name}. On Prism: ${event.title}`;
  return {
    title,
    description,
    alternates: { canonical: `/story/${id}` },
    openGraph: { type: "article", siteName: "Prism", title, description, url: `/story/${id}/quote/${n}` },
    twitter: { card: "summary_large_image", title, description },
  };
}

export default async function QuotePage({ params }: { params: Promise<{ id: string; n: string }> }) {
  const { id, n } = await params;
  let event;
  try {
    event = await fetchEvent(id);
  } catch {
    notFound();
  }
  if (!findQuote(event.claims, n)) notFound();
  return StoryPage({ params: Promise.resolve({ id }) });
}
