import { API_URL } from "@/lib/api";
import { SITE_URL } from "@/lib/site";

// The archive. sitemap.xml lists the static pages, the arcs and the freshest
// hundred records; this lists every served record (audit H30 — past the
// freshest hundred, the archive was invisible to crawlers within days). One
// file until the corpus passes the protocol's 50,000 URLs, then an index.
//
// Rendered per request and cached at the edge for an hour, never prerendered:
// the first deploy baked an EMPTY file because the build ran while the API
// was still mid-deploy, and Search Console reads an empty sitemap as
// "Couldn't fetch". An unreachable API is a 503 with Retry-After, so the
// crawler comes back rather than recording a sitemap with nothing in it.
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  let records: { id: string; last_updated_at: string | null }[];
  try {
    const res = await fetch(`${API_URL}/api/v1/sitemap/records`, { cache: "no-store" });
    if (!res.ok) throw new Error(`api ${res.status}`);
    records = (await res.json()).records ?? [];
  } catch {
    return new Response("records unavailable", { status: 503, headers: { "Retry-After": "300" } });
  }
  const body = records
    .map((r) => `  <url><loc>${SITE_URL}/story/${r.id}</loc>${r.last_updated_at ? `<lastmod>${r.last_updated_at}</lastmod>` : ""}</url>`)
    .join("\n");
  const xml = `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`;
  return new Response(xml, {
    headers: {
      "Content-Type": "application/xml; charset=utf-8",
      "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400",
    },
  });
}
