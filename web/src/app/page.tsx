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
export default async function Page() {
  if ((await cookies()).has(RETURNING_COOKIE)) redirect("/feed");
  return Landing();
}
