import { NextResponse, type NextRequest } from "next/server";

import { API_URL } from "@/lib/api";

// A founder link's short address (/admin/marketing): readprism.news/go/<code>
// opens the page the link was made for, with its tags, and the page counts the
// visit (UsageBeacon) — this route counts nothing, so a link preview or a
// crawler following it is never a visit. A code that is not a link opens the
// front page rather than an error. Never cached: the redirect's target is a
// lookup, and a link made a minute ago must work at once.
const CODE = /^[2-9a-hjkmnp-z]{6}$/; // common/share_links.CODE

type Link = { path: string; tags: Record<string, string> };

async function lookup(code: string): Promise<Link | null> {
  if (!CODE.test(code)) return null;
  try {
    const res = await fetch(`${API_URL}/api/v1/links/${code}`, { cache: "no-store" });
    return res.ok ? ((await res.json()) as Link) : null;
  } catch {
    return null; // the API is away: the front page, not an error page
  }
}

export async function GET(req: NextRequest, { params }: { params: Promise<{ code: string }> }) {
  const link = await lookup((await params).code.toLowerCase());
  // Only a path on this site: the API says so, and this makes sure of it.
  const safe = link && link.path.startsWith("/") && !link.path.startsWith("//");
  const target = new URL(safe ? link.path : "/", req.nextUrl.origin);
  if (safe) for (const [k, v] of Object.entries(link.tags)) target.searchParams.set(k, v);
  return NextResponse.redirect(target, { status: 307, headers: { "Cache-Control": "no-store", "X-Robots-Tag": "noindex" } });
}
