import { fetchFeed, type FeedItem } from "@/lib/api";
import { SITE_URL } from "@/lib/site";

// Google News sitemap: the records of the last two days (Google reads no
// older), each with its first-reported date and headline under the
// publication "Prism". Next's MetadataRoute.Sitemap has no news namespace, so
// this is a plain XML route. Revalidated with the feed's own cache.
export const revalidate = 900;

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export async function GET() {
  let items: FeedItem[] = [];
  try {
    items = await fetchFeed({ sort: "latest", limit: 500 });
  } catch {
    // API down: an empty, valid sitemap rather than a 500.
  }
  // A record's publication date is when it was first reported (the latest
  // report's time is the nearest the feed row carries), never when we last
  // touched it — Google reads a re-dated article as gaming.
  const published = (e: FeedItem) => e.latest_published_at ?? e.last_updated_at;
  const cutoff = Date.now() - 2 * 24 * 3600 * 1000;
  const recent = items.filter((e) => Date.parse(published(e)) >= cutoff).slice(0, 1000);
  const body = recent
    .map(
      (e) => `  <url>
    <loc>${SITE_URL}/story/${e.id}</loc>
    <news:news>
      <news:publication><news:name>Prism</news:name><news:language>en</news:language></news:publication>
      <news:publication_date>${new Date(published(e)).toISOString()}</news:publication_date>
      <news:title>${esc(e.title)}</news:title>
    </news:news>
    <lastmod>${new Date(e.last_updated_at).toISOString()}</lastmod>
  </url>`,
    )
    .join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
${body}
</urlset>
`;
  return new Response(xml, { headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=900, s-maxage=900" } });
}
