import type { MetadataRoute } from "next";
import { fetchFeed, fetchSubjects, fetchTrending } from "@/lib/api";
import { SECTOR_GROUPS } from "@/lib/sectors";
import { SITE_URL } from "@/lib/site";

export const revalidate = 3600;

// Every public address: the static pages, the six subjects, the developing
// stories and the day's records. Search engines discover the records here;
// the news sitemap (news-sitemap.xml) carries the last two days for Google
// News. Static pages always render even if the API is down.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  let subjectNodes: { path: string; depth: number }[] = [];
  try {
    const tree = await fetchSubjects();
    subjectNodes = (tree?.nodes ?? []).filter((n) => (n.story_count ?? 0) > 0);
  } catch {
    // API down → the rest of the sitemap still serves.
  }
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/feed`, changeFrequency: "hourly", priority: 0.9 },
    { url: `${SITE_URL}/trending`, changeFrequency: "hourly", priority: 0.9 },
    { url: `${SITE_URL}/about`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/sources`, changeFrequency: "daily", priority: 0.4 },
    { url: `${SITE_URL}/plus`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/pulse`, changeFrequency: "daily", priority: 0.4 },
    { url: `${SITE_URL}/privacy`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/terms`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/refunds`, changeFrequency: "yearly", priority: 0.2 },
    ...SECTOR_GROUPS.map((g) => ({ url: `${SITE_URL}/sector/${g.slug}`, changeFrequency: "hourly" as const, priority: 0.7 })),
    // Every node of the subject tree that has stories under it. A node with
    // none is left out rather than offered to a crawler as an empty room.
    ...subjectNodes.map((n) => ({
      url: `${SITE_URL}/subject/${n.path.split(".").join("/")}`,
      changeFrequency: "hourly" as const,
      priority: n.depth === 1 ? 0.7 : 0.6,
    })),
  ];

  let stories: MetadataRoute.Sitemap = [];
  let arcs: MetadataRoute.Sitemap = [];
  try {
    // ponytail: one feed page — the API caps a page at 100, so this is the
    // freshest hundred records; the news sitemap carries the same window.
    // Page through with an offset if older records need listing.
    const feed = await fetchFeed({ limit: 100 });
    stories = feed.map((e) => ({
      url: `${SITE_URL}/story/${e.id}`,
      lastModified: e.last_updated_at,
      changeFrequency: "hourly" as const,
      priority: 0.7,
    }));
  } catch {
    // API down → still serve the static pages rather than a 500.
  }
  try {
    const trending = await fetchTrending({ state: null, sector: null, limit: 100 });
    arcs = trending.map((s) => ({
      url: `${SITE_URL}/trending/${s.slug}`,
      lastModified: s.last_updated_at ?? undefined,
      changeFrequency: "hourly" as const,
      priority: 0.8,
    }));
  } catch {
    // as above
  }

  return [...staticPages, ...arcs, ...stories];
}
