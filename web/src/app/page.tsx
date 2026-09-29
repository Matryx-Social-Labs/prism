import type { Metadata } from "next";
import { social } from "@/lib/seo";
import { cookies } from "next/headers";
import { redirect } from "next/navigation";
import { Landing } from "@/components/Landing";
import { RETURNING_COOKIE } from "@/lib/returning";

// `/` is the landing for a first visitor and the chart for everyone else
// (founder decision D5 revised, 2026-09-16). "Everyone else" is anyone who has
// reached the chart once — FrontPage sets the cookie — so the pitch is read
// once and the product is what the domain opens to after that. The redirect is
// server-side: no flash of marketing for a returning reader, and a crawler
// (no cookie) always gets the landing.
// The one address a first crawl lands on had no canonical while every other
// route did (audit); the landing is `/`, the chart is `/feed`.
// The search title names the category (several products are called Prism);
// the share card keeps the promise, as the landing's H1 does.
const DESCRIPTION = "One page per Indian news story, from a public list of outlets in English and Indian languages: every report, who covered it, and who said what, word for word.";
export const metadata: Metadata = {
  title: { absolute: "Prism: India's verifiable news record" },
  description: DESCRIPTION,
  alternates: { canonical: "/" },
  ...social("Prism: Follow the story, not the headlines.", DESCRIPTION, "/"),
};

/** The words a link to `/` carried that say where it came from; they go on to
 *  /feed with a returning reader, or the visit loses its link (UsageBeacon). */
function carried(params: Record<string, string | string[] | undefined>): string {
  const kept = Object.entries(params).filter(
    (e): e is [string, string] => typeof e[1] === "string" && (e[0] === "ref" || e[0] === "s" || e[0].startsWith("utm_")),
  );
  return kept.length ? `?${new URLSearchParams(kept)}` : "";
}

export default async function Page({ searchParams }: { searchParams?: Promise<Record<string, string | string[] | undefined>> }) {
  if ((await cookies()).has(RETURNING_COOKIE)) redirect(`/feed${carried((await searchParams) ?? {})}`);
  return Landing();
}
