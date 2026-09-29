import { API_URL } from "@/lib/api";
import { atomFeed, type AtomRecord } from "@/lib/atom";

// The Atom feed of records (RFC 4287) for feed readers and their directories
// (Feedly, Inoreader, Feedspot): the newest fifty records two or more monitored
// outlets reported, the records sitemap's rule, applied by the API
// (/api/v1/sitemap/atom). Per request and cached at the edge for fifteen
// minutes, as news-sitemap.xml and for its reason: an unreachable API is a 503
// with Retry-After, never an empty feed a reader would record as "no news".
export const dynamic = "force-dynamic";

export async function GET(): Promise<Response> {
  let records: AtomRecord[];
  try {
    const res = await fetch(`${API_URL}/api/v1/sitemap/atom`, { cache: "no-store" });
    if (!res.ok) throw new Error(`api ${res.status}`);
    records = (await res.json()).records ?? [];
  } catch {
    return new Response("records unavailable", { status: 503, headers: { "Retry-After": "300" } });
  }
  return new Response(atomFeed(records), {
    headers: { "Content-Type": "application/atom+xml; charset=utf-8", "Cache-Control": "public, s-maxage=900, stale-while-revalidate=3600" },
  });
}
