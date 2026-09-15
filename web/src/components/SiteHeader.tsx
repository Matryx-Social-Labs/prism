"use client";

// Global brand header. On mobile it is HIDDEN on app routes that carry their own
// in-page header (the chart at / and /feed has its masthead; trending/you show a
// scope chip; story pins its own rail) — otherwise the reader gets two stacked
// headers. Desktop always shows it. About / onboarding / auth keep it on mobile too.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PrismMark } from "@/components/PrismMark";
import { HeaderNav } from "@/components/HeaderNav";

// "/label" is here for a slightly different reason than the reader surfaces: it is
// a single-purpose task page opened from an unguessable link, often by someone who
// does not use Prism at all. On a phone the marketing nav ("Sign in", "Get your
// feed") is an invitation to leave in the middle of a judgement.
const APP_ROUTES = ["/feed", "/trending", "/pulse", "/search", "/sector", "/you", "/account", "/interests", "/watchlist", "/story", "/label"];

export function SiteHeader() {
  const pathname = usePathname();
  const isApp = pathname === "/" || APP_ROUTES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  return (
    <>
      <div className="spectrum-bar h-[3px] w-full" aria-hidden />
      <header
        className={`${isApp ? "hidden lg:block" : ""} sticky top-0 z-40 border-b backdrop-blur-md`}
        style={{ borderColor: "var(--line)", background: "var(--glass)" }}
      >
        {/* h-14: a fixed row, not padding, so the height is the same signed in
            (32px avatar) and out (36px CTA) — the sector strip sticks under it
            at a known offset (57px with the border) on every surface. */}
        <div className="mx-auto flex h-14 max-w-[1280px] items-center justify-between gap-3 px-5 sm:px-8 xl:px-10">
          <Link href="/" className="flex items-center gap-2.5" style={{ color: "var(--ink)" }}>
            <PrismMark />
            <span className="text-xl font-semibold tracking-tight" style={{ fontFamily: "var(--font-display), serif" }}>
              Prism
            </span>
          </Link>
          <HeaderNav />
        </div>
      </header>
    </>
  );
}
