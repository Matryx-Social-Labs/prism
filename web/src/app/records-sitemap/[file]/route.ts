import { API_URL } from "@/lib/api";
import { SITE_URL } from "@/lib/site";
import { lastmodTag, unavailable, xmlResponse } from "@/lib/sitemapXml";

// One month of records-sitemap.xml: the indexed records Prism first saw that
// month, which never changes, so a record stays in one file. `lastmod` is the
// newest report's time (api/routes/meta.py), not the projection rebuild clock.
export const dynamic = "force-dynamic";

const MONTH_FILE = /^(\d{4}-(?:0[1-9]|1[0-2]))\.xml$/;

export async function GET(_req: Request, { params }: { params: Promise<{ file: string }> }): Promise<Response> {
  const month = MONTH_FILE.exec((await params).file)?.[1];
  if (!month) return new Response("not found", { status: 404 });
  let records: { id: string; lastmod?: string | null }[];
  try {
    const res = await fetch(`${API_URL}/api/v1/sitemap/records?month=${month}`, { cache: "no-store" });
    if (!res.ok) throw new Error(`api ${res.status}`);
    records = (await res.json()).records ?? [];
  } catch {
    return unavailable();
  }
  const body = records.map((r) => `  <url><loc>${SITE_URL}/story/${r.id}</loc>${lastmodTag(r.lastmod)}</url>`).join("\n");
  return xmlResponse(`<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${body}\n</urlset>\n`);
}
