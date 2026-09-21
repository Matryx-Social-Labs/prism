"use client";

// The desktop top bar (DESIGN.md § Layout): brand · Today · Stories · Pulse ·
// Watchlist · a visible search field · theme · Sign in or the avatar. On the
// phone it is hidden on app routes — the masthead and the bottom tab bar are the
// chrome there — and shown on the landing, onboarding and auth, where a phone
// reader still needs the brand and a way in.
import { usePathname } from "next/navigation";
import { Brand } from "@/components/Brand";
import { HeaderNav } from "@/components/HeaderNav";

// "/label" is a single-purpose task page opened from an unguessable link, often
// by someone who does not use Prism at all; the product nav is an invitation to
// leave in the middle of a judgement.
const APP_ROUTES = ["/feed", "/trending", "/pulse", "/search", "/sector", "/you", "/account", "/interests", "/watchlist", "/story", "/label"];

export function SiteHeader() {
  const pathname = usePathname();
  const isApp = APP_ROUTES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  return (
    <header
      className={`${isApp ? "hidden lg:block" : ""} site-header glass sticky top-0 z-40 border-b`}
      style={{ borderColor: "var(--line)", height: "var(--topbar)" }}
    >
      <div className="mx-auto grid h-full max-w-[var(--shell)] grid-cols-[auto_minmax(0,1fr)] items-center gap-8 px-5 sm:px-8 xl:px-10">
        <Brand />
        <HeaderNav />
      </div>
    </header>
  );
}
