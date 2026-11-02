import { API_URL } from "@/lib/api";
import { SITE_URL } from "@/lib/site";
import { lastmodTag, unavailable, xmlResponse } from "@/lib/sitemapXml";

// The archive, as an index of one file per month (records-sitemap/<YYYY-MM>.xml).
// sitemap.xml lists the static pages, the arcs and the freshest hundred records;
// these list every indexed record (audit H30). One file stopped at the protocol's
// 50,000 URLs, and October alone added 15,257 records (2026-11-02). The address
// is the one submitted to Search Console, so it stays and becomes the index.
//
// Rendered per request and cached at the edge for an hour, never prerendered:
// the first deploy baked an EMPTY file because the build ran while the API
// was still mid-deploy, and Search Console reads an empty sitemap as
// "Couldn't fetch". An unreachable API is a 503 with Retry-After, so the
// crawler comes back rather than recording a sitemap with nothing in it.
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  let months: { month: string; lastmod: string | null }[];
  try {
    const res = await fetch(`${API_URL}/api/v1/sitemap/records/months`, { cache: "no-store" });
    if (!res.ok) throw new Error(`api ${res.status}`);
    months = (await res.json()).months ?? [];
  } catch {
    return unavailable();
  }
  const body = months
    .map((m) => `  <sitemap><loc>${SITE_URL}/records-sitemap/${m.month}.xml</loc>${lastmodTag(m.lastmod)}</sitemap>`)
    .join("\n");
  return xmlResponse(`<?xml version="1.0" encoding="UTF-8"?>\n<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</sitemapindex>\n`);
}
