import { API_URL } from "@/lib/api";
import { SITE_URL } from "@/lib/site";

export const revalidate = 3600;

// The archive. sitemap.xml lists the static pages, the arcs and the freshest
// hundred records; this lists every served record (audit H30 — past the
// freshest hundred, the archive was invisible to crawlers within days). One
// file until the corpus passes the protocol's 50,000 URLs, then an index.
export async function GET(): Promise<Response> {
  let records: { id: string; last_updated_at: string | null }[] = [];
  try {
    const res = await fetch(`${API_URL}/api/v1/sitemap/records`, { next: { revalidate: 3600 } });
    if (res.ok) records = (await res.json()).records ?? [];
  } catch {
    // API down → an empty but valid sitemap rather than a 500.
  }
  const body = records
    .map((r) => `  <url><loc>${SITE_URL}/story/${r.id}</loc>${r.last_updated_at ? `<lastmod>${r.last_updated_at}</lastmod>` : ""}</url>`)
    .join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
  return new Response(xml, { headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, max-age=3600" } });
}
