import type { MetadataRoute } from "next";
import { fetchFeed } from "@/lib/api";
import { SITE_URL } from "@/lib/site";

export const revalidate = 3600;

// Lists public pages + story URLs so search engines can discover the stories the
// SEO metadata describes. Static pages always render even if the API is down.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const staticPages: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/`, changeFrequency: "daily", priority: 1 },
    { url: `${SITE_URL}/feed`, changeFrequency: "daily", priority: 0.8 },
    { url: `${SITE_URL}/about`, changeFrequency: "monthly", priority: 0.5 },
  ];

  let stories: MetadataRoute.Sitemap = [];
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

  return [...staticPages, ...stories];
}
