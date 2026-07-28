"use client";

// Global brand header. On mobile it is HIDDEN on app routes that carry their own
// in-page header (feed/trending/you show a scope chip; story pins its own rail) —
// otherwise the reader gets two stacked headers. Desktop always shows it (desktop
// is redone separately). Landing / about / onboarding / auth keep it on mobile too.
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PrismMark } from "@/components/PrismMark";
import { HeaderNav } from "@/components/HeaderNav";

const APP_ROUTES = ["/feed", "/trending", "/pulse", "/search", "/sector", "/you", "/account", "/interests", "/watchlist", "/story"];

export function SiteHeader() {
  const pathname = usePathname();
  const isApp = APP_ROUTES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  return (
    <>
      <div className="spectrum-bar h-[3px] w-full" aria-hidden />
      <header
        className={`${isApp ? "hidden lg:block" : ""} sticky top-0 z-40 border-b backdrop-blur-md`}
        style={{ borderColor: "var(--line)", background: "var(--glass)" }}
      >
        <div className="mx-auto flex max-w-[1280px] items-center justify-between gap-3 px-5 py-[11px] sm:px-8 xl:px-10">
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
