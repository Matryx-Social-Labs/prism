"use client";

// The desktop top bar (DESIGN.md § Layout): brand · Today · Stories · Pulse ·
// Watchlist · a visible search field · theme · Sign in or the avatar. On the
// phone it is hidden on app routes — the masthead and the bottom tab bar are the
// chrome there — and shown on the landing, onboarding and auth, where a phone
// reader still needs the brand and a way in.
import { usePathname } from "next/navigation";
import { Brand } from "@/components/Brand";
import { HeaderNav } from "@/components/HeaderNav";
import { ThemeToggle } from "@/components/ThemeToggle";

// On the phone these draw their own top: the masthead with the tab bar, or a back bar.
const APP_ROUTES = ["/feed", "/trending", "/pulse", "/search", "/sector", "/you", "/account", "/interests", "/watchlist", "/story", "/entity", "/subject", "/corrections", "/sources", "/privacy", "/terms", "/refunds"];

// Signing in and setting up a feed get the brand-only bar (Design System v2 ·
// Accounts board): no nav to wander off through, no "Sign in" on the sign-in page.
const BARE_ROUTES = ["/signin", "/auth", "/onboarding"];

// Tools with their own chrome: the founders' admin (the sidebar, Design System v2 ·
// AdminShell) and the labeller (its own bar: brand · Label · email). "/label" is a
// single-purpose task page opened from an unguessable link, often by someone who
// does not use Prism at all; the product nav is an invitation to leave in the
// middle of a judgement. No reader top bar over them, no reader footer under them.
export const OWN_CHROME = ["/admin", "/label"];

const under = (pathname: string, routes: string[]) => routes.some((p) => pathname === p || pathname.startsWith(`${p}/`));

/**
 * Pages whose phone chrome is this bar (the landing, /about, /plus): lockup · one control,
 * no theme toggle (Claude Design · screens/PhoneBar.html). The footer shows on a phone
 * exactly here, because its Appearance row is where the theme control went.
 */
export const hasPhoneBar = (pathname: string) => !under(pathname, [...APP_ROUTES, ...BARE_ROUTES, ...OWN_CHROME]);

export function SiteHeader() {
  const pathname = usePathname();
  if (under(pathname, OWN_CHROME)) return null;
  if (under(pathname, BARE_ROUTES)) {
    return (
      <header className="glass sticky top-0 z-40 h-[var(--masthead)] border-b lg:h-[var(--topbar)]" style={{ borderColor: "var(--line)" }}>
        <div className="mx-auto flex h-full max-w-[var(--shell)] items-center gap-2 px-[var(--gutter)]">
          <Brand size={22} />
          <span className="flex-1" />
          <ThemeToggle />
        </div>
      </header>
    );
  }
  const isApp = under(pathname, APP_ROUTES);
  return (
    <header
      className={`${isApp ? "hidden lg:block" : ""} glass sticky top-0 z-40 h-[var(--masthead)] border-b sm:h-[var(--topbar)]`}
      style={{ borderColor: "var(--line)" }}
    >
      <div className="mx-auto flex h-full max-w-[var(--shell)] items-center gap-3 px-[var(--gutter)] sm:gap-5">
        {/* The phone bar (below 640) sets the lockup at 20, the tablet and desk bar at 24 (screens/PhoneBar.html). */}
        <span className="sm:hidden"><Brand size={20} /></span>
        <span className="hidden sm:block"><Brand size={24} /></span>
        <HeaderNav />
      </div>
    </header>
  );
}
