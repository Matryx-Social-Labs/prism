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

// The founders' admin is a tool with its own chrome (the sidebar, Design System v2 ·
// AdminShell): no reader top bar over it, no reader footer under it.
export const OWN_CHROME = ["/admin"];

export function SiteHeader() {
  const pathname = usePathname();
  if (OWN_CHROME.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return null;
  const isApp = APP_ROUTES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  return (
    <header
      className={`${isApp ? "hidden lg:block" : ""} glass sticky top-0 z-40 border-b`}
      style={{ borderColor: "var(--line)", height: "var(--topbar)" }}
    >
      <div className="mx-auto flex h-full max-w-[var(--shell)] items-center gap-5 px-[var(--gutter)]">
        <Brand size={24} />
        <HeaderNav />
      </div>
    </header>
  );
}
