import { StoriesPage } from "@/components/StoriesPage";
import { fetchTrending, type TrendingStory } from "@/lib/api";
import { itemListLd, jsonLd, storyListItems } from "@/lib/seo";
import { SITE_URL } from "@/lib/site";

// Stories (the URL stays /trending): the national list is fetched here so the
// developing stories are in the HTML; a reader scoped to their state
// re-fetches on the client. Revalidated every two minutes with the API's cache.
export const revalidate = 120;

export default async function TrendingPage() {
  let initial: TrendingStory[] | null = null;
  try {
    initial = await fetchTrending({ state: null, sector: null, limit: 24 });
  } catch {
    // API unreachable at render: the client fetches as before.
  }
  return (
    <>
      {initial && initial.length > 0 && (
        <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: jsonLd(itemListLd("Stories developing over days", `${SITE_URL}/trending`, storyListItems(initial))) }} />
      )}
      <StoriesPage initial={initial} />
    </>
  );
}
