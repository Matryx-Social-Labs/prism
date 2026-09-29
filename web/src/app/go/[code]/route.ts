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
  const origin = req.nextUrl.origin;
  let target = new URL("/", origin);
  if (link?.path.startsWith("/")) {
    target = new URL(link.path, origin);
    for (const [k, v] of Object.entries(link.tags)) target.searchParams.set(k, v);
  }
  // Only this site, whatever the API answered: a path like "/\evil.example"
  // resolves to another host, so the check is on where the URL ends up.
  if (target.origin !== origin) target = new URL("/", origin);
  return NextResponse.redirect(target, { status: 307, headers: { "Cache-Control": "no-store", "X-Robots-Tag": "noindex" } });
}
