import { FrontPage } from "@/components/FrontPage";
import { fetchArchive, fetchFeed, type ArchiveReading, type FeedItem } from "@/lib/api";
import { FEED_WINDOW } from "@/lib/feedWindow";
import { feedListItems, itemListLd, jsonLd } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// Same chart as `/` — every existing link, redirect and tab that says /feed
// still lands on today's list. The ALL list is fetched here so the rows are
// in the HTML (crawlers and answer engines read it without JS; the reader's
// own slice re-fetches on the client only when it differs). Revalidated
// every minute with the API's own cache.
export const revalidate = 60;

export default async function FeedPage() {
  let initial: FeedItem[] | null = null;
  try {
    initial = await fetchFeed({ sort: "latest", limit: FEED_WINDOW });
  } catch {
    // API unreachable at render: the client fetches as before.
  }
  // The days before today, for the day strip; without them the strip is left out.
  const days: ArchiveReading[] | null = (await fetchArchive().catch(() => null))?.days ?? null;
  return (
    <>
      {initial && initial.length > 0 && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(itemListLd("Today's record", `${SITE_URL}/feed`, feedListItems(initial))) }} />
      )}
      <FrontPage initial={initial} days={days} />
    </>
  );
}
