import { API_URL } from "@/lib/api";
import { SITE_URL } from "@/lib/site";

// The actors worth a crawl: every entity the API reports in at least
// INDEXABLE_MIN_RECORDS served records (api/routes/entity.py). The thin ones
// are deliberately absent — their pages exist for the reader and carry
// `noindex`, so listing them would spend crawl budget the records need.
//
// Rendered per request, cached at the edge: a build-time render once baked an
// empty records sitemap because the API was mid-deploy, and Search Console
// reads an empty sitemap as "Couldn't fetch".
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  let entities: { slug: string; last_updated_at: string | null }[];
  try {
    const res = await fetch(`${API_URL}/api/v1/sitemap/entities`, { cache: "no-store" });
    if (!res.ok) throw new Error(`api ${res.status}`);
    entities = (await res.json()).entities ?? [];
  } catch {
    return new Response("entities unavailable", { status: 503, headers: { "Retry-After": "300" } });
  }
  const body = entities
    .map((e) => `  <url><loc>${SITE_URL}/entity/${encodeURIComponent(e.slug)}</loc>${e.last_updated_at ? `<lastmod>${e.last_updated_at}</lastmod>` : ""}</url>`)
    .join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
