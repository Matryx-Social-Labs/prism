// What every sitemap route answers with (records-sitemap.xml and its month files).

export const lastmodTag = (t: string | null | undefined) => (t ? `<lastmod>${t}</lastmod>` : "");

/** The API cannot answer: a 503 the crawler retries, never an empty sitemap ("Couldn't fetch"). */
export const unavailable = () => new Response("records unavailable", { status: 503, headers: { "Retry-After": "300" } });

export const xmlResponse = (xml: string) =>
  new Response(xml, {
    headers: { "Content-Type": "application/xml; charset=utf-8", "Cache-Control": "public, s-maxage=3600, stale-while-revalidate=86400" },
  });
