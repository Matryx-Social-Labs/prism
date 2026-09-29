import { API_URL } from "@/lib/api";
import { SITE_URL } from "@/lib/site";

// Google News sitemap: every record first reported in the last two days (Google
// reads no older) that asks to be indexed, with that first report's date and the
// headline under the publication "Prism". Its own API query
// (/api/v1/sitemap/news): filtering the feed's newest hundred listed about 10 of
// the hundreds eligible (audit A4). Next's MetadataRoute.Sitemap has no news
// namespace, so this is a plain XML route.
//
// Per request and cached at the edge for fifteen minutes, as records-sitemap.xml
// and for its reason: an unreachable API is a 503 with Retry-After, never an
// empty file Search Console records as the sitemap.
export const dynamic = "force-dynamic";

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

export async function GET(): Promise<Response> {
  let records: { id: string; title: string; published_at: string }[];
  try {
    const res = await fetch(`${API_URL}/api/v1/sitemap/news`, { cache: "no-store" });
    if (!res.ok) throw new Error(`api ${res.status}`);
    records = (await res.json()).records ?? [];
  } catch {
    return new Response("records unavailable", { status: 503, headers: { "Retry-After": "300" } });
  }
  // The publication date is the first report's, never when we last touched the
  // record — Google reads a re-dated article as gaming.
  const body = records
    .map(
      (e) => `  <url>
    <loc>${SITE_URL}/story/${e.id}</loc>
    <news:news>
      <news:publication><news:name>Prism</news:name><news:language>en</news:language></news:publication>
      <news:publication_date>${new Date(e.published_at).toISOString()}</news:publication_date>
      <news:title>${esc(e.title)}</news:title>
    </news:news>
  </url>`,
    )
    .join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:news="http://www.google.com/schemas/sitemap-news/0.9">
${body}
</urlset>
`;
  return new Response(xml, { headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, s-maxage=900" } });
}
