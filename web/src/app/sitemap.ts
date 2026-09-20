import type { MetadataRoute } from "next";
import { fetchFeed, fetchTrending } from "@/lib/api";
import { SECTOR_GROUPS } from "@/lib/sectors";
import { SITE_URL } from "@/lib/site";

export const revalidate = 3600;

// Every public address: the static pages, the six subjects, the developing
// stories and the day's records. Search engines discover the records here;
// the news sitemap (news-sitemap.xml) carries the last two days for Google
// News. Static pages always render even if the API is down.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/feed`, changeFrequency: "hourly", priority: 0.9 },
    { url: `${SITE_URL}/trending`, changeFrequency: "hourly", priority: 0.9 },
    { url: `${SITE_URL}/about`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/plus`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/pulse`, changeFrequency: "daily", priority: 0.4 },
    { url: `${SITE_URL}/privacy`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/terms`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/refunds`, changeFrequency: "yearly", priority: 0.2 },
    ...SECTOR_GROUPS.map((g) => ({ url: `${SITE_URL}/sector/${g.slug}`, changeFrequency: "hourly" as const, priority: 0.7 })),
  ];

  let stories: MetadataRoute.Sitemap = [];
  let arcs: MetadataRoute.Sitemap = [];
  try {
    // ponytail: single feed page (cap ~500). Add pagination if the corpus outgrows it.
    const feed = await fetchFeed({ limit: 500 });
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
