import type { MetadataRoute } from "next";
import { fetchArchive, fetchFeed, fetchStateHubs, fetchSubjects, fetchTrending } from "@/lib/api";
import { SECTOR_GROUPS, sectorPageFor } from "@/lib/sectors";
import { SITE_URL } from "@/lib/site";
import { newsTime } from "@/lib/dateline";

export const revalidate = 3600;
// Every fetch below is asked for the same hour: a shorter one would set the
// sitemap's clock instead (scripts/check-cache-windows.mjs).

// Every public address: the static pages, the six subjects, the developing
// stories and the day's records. Search engines discover the records here;
// the news sitemap (news-sitemap.xml) carries the last two days for Google
// News. Static pages always render even if the API is down.
export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  let subjectNodes: { path: string; depth: number }[] = [];
  try {
    const tree = await fetchSubjects(revalidate);
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
    { url: `${SITE_URL}/corrections`, changeFrequency: "daily", priority: 0.4 },
    { url: `${SITE_URL}/plus`, changeFrequency: "monthly", priority: 0.5 },
    { url: `${SITE_URL}/privacy`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/terms`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/refunds`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/delivery`, changeFrequency: "yearly", priority: 0.2 },
    { url: `${SITE_URL}/grievance`, changeFrequency: "monthly", priority: 0.3 },
    { url: `${SITE_URL}/press`, changeFrequency: "monthly", priority: 0.3 },
    { url: `${SITE_URL}/for-publishers`, changeFrequency: "monthly", priority: 0.3 },
    ...SECTOR_GROUPS.map((g) => ({ url: `${SITE_URL}/sector/${g.slug}`, changeFrequency: "hourly" as const, priority: 0.7 })),
    // Every node of the subject tree that has stories under it. A node with
    // none is left out rather than offered to a crawler as an empty room, and
    // so is a node whose records its /sector page already lists (sectorPageFor).
    // /pulse is not here either: it renders in the browser, 26 words to a crawler.
    ...subjectNodes.filter((n) => !sectorPageFor(n.path)).map((n) => ({
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
    const feed = await fetchFeed({ limit: 100 }, revalidate);
    // Only what asks to be indexed: two outlets or more, a verified story (lib/seo NOT_INDEXED).
    stories = feed.filter((e) => e.indexable !== false).map((e) => ({
      url: `${SITE_URL}/story/${e.id}`,
      // The newest report, as records-sitemap.xml has it: not the rebuild clock (audit 01 P2-11).
      // Never later than the record's own rebuild: a feed can stamp a report in
      // the future, and the API's sitemaps clamp the same way (review 2026-09-29).
      lastModified: Date.parse(newsTime(e)) > Date.parse(e.last_updated_at) ? e.last_updated_at : newsTime(e),
      changeFrequency: "hourly" as const,
      priority: 0.7,
    }));
  } catch {
    // API down → still serve the static pages rather than a 500.
  }
  try {
    const trending = await fetchTrending({ state: null, sector: null, limit: 100 }, revalidate);
    // As the story page's robots: verified, two or more developments from two or more outlets.
    arcs = trending.filter((s) => s.boundary_status === "verified" && s.developments >= 2 && s.source_count >= 2).map((s) => ({
      url: `${SITE_URL}/trending/${s.slug}`,
      lastModified: s.last_updated_at ?? undefined,
      changeFrequency: "hourly" as const,
      priority: 0.8,
    }));
  } catch {
    // as above
  }

  // The state hubs and the day archive (audit 02, P1): their indexes always,
  // and a hub or a day only when it asks to be indexed (the API's floors). An
  // API that cannot answer leaves both out rather than guessing.
  const hubs = await fetchStateHubs(revalidate).catch(() => null);
  const archive = await fetchArchive(revalidate).catch(() => null);
  const places: MetadataRoute.Sitemap = [
    { url: `${SITE_URL}/state`, changeFrequency: "daily", priority: 0.6 },
    ...(hubs?.states ?? []).filter((s) => s.indexable).map((s) => ({ url: `${SITE_URL}/state/${s.slug}`, changeFrequency: "hourly" as const, priority: 0.7 })),
    { url: `${SITE_URL}/archive`, changeFrequency: "daily", priority: 0.5 },
    ...(archive?.days ?? []).filter((d) => d.indexable).map((d) => ({ url: `${SITE_URL}/feed/${d.date}`, changeFrequency: "weekly" as const, priority: 0.5 })),
  ];

  return [...staticPages, ...places, ...arcs, ...stories];
}
