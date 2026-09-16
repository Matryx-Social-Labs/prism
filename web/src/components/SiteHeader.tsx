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
  const isApp = APP_ROUTES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  // No spectrum bar above the header: colour in chrome is a lens speaking, and
  // none speaks here. The mark carries the brand on its own.
  return (
    <>
      <header
        className={`${isApp ? "hidden lg:block" : ""} sticky top-0 z-40 border-b backdrop-blur-md`}
        style={{ borderColor: "var(--line)", background: "var(--glass)" }}
      >
        {/* h-14: a fixed row, not padding, so the height is the same signed in
            (32px avatar) and out (36px CTA) — the sector strip sticks under it
            at a known offset (57px with the border) on every surface. */}
        <div className="mx-auto flex h-14 max-w-[1280px] items-center justify-between gap-3 px-5 sm:px-8 xl:px-10">
          {/* One wordmark treatment everywhere: the mark, then PRISM in the structural voice (Masthead does the same). */}
          <Link href="/" className="flex items-center gap-2" style={{ color: "var(--ink)" }} aria-label="Prism">
            <PrismMark />
            <span className="font-display text-[26px] leading-none tracking-[0.01em]">PRISM</span>
          </Link>
          <HeaderNav />
        </div>
      </header>
    </>
  );
}
