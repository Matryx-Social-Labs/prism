"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { ThemeToggle } from "@/components/ThemeToggle";
import { useSession } from "@/lib/session";

const NAV = [
  { href: "/feed", label: "Today" },
  { href: "/trending", label: "Trending" },
  { href: "/pulse", label: "Pulse" },
  { href: "/watchlist", label: "Watchlist" },
];

export function HeaderNav() {
  const pathname = usePathname();
  const session = useSession();

  const active = (href: string) =>
    href === "/feed"
      ? ["/feed", "/sector"].some((p) => pathname === p || pathname.startsWith(`${p}/`))
      : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <nav className="flex items-center gap-1 sm:gap-2">
      {/* Text links live on desktop only; on mobile the bottom tab bar owns
          navigation, so the header stays uncluttered. No lens control here:
          the lens is set in "Your Prism" (/interests) and flipped per-story
          in the story view — the header stays monochrome chrome. */}
      {NAV.map((n) => (
        <Link
          key={n.href}
          href={n.href}
          className="hidden px-2 py-1.5 text-[13.5px] font-medium sm:block"
          style={{ color: active(n.href) ? "var(--ink)" : "var(--ink-muted)" }}
        >
          {n.label}
        </Link>
      ))}
      <Link
        href="/search"
        aria-label="Search"
        className="hidden h-8 w-8 items-center justify-center rounded-full sm:flex"
        style={{ color: active("/search") ? "var(--ink)" : "var(--ink-muted)" }}
      >
        <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </Link>
      {!session && (
        <Link
          href="/signin"
          className="hidden px-2 py-1.5 text-[13.5px] font-medium sm:block"
          style={{ color: active("/signin") ? "var(--ink)" : "var(--ink-muted)" }}
        >
          Sign in
        </Link>
      )}
      <ThemeToggle />
      {session ? (
        <Link
          href="/account"
          className="flex h-7 w-7 items-center justify-center rounded-full border text-[12px] font-semibold uppercase"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
          title={`Signed in as ${session.email}`}
        >
          {session.email.slice(0, 1)}
        </Link>
      ) : (
        <Link
          href="/onboarding"
          className="whitespace-nowrap rounded-full px-4 py-2 text-[13px] font-semibold transition hover:opacity-85 sm:px-[18px]"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          Get your feed
        </Link>
      )}
    </nav>
  );
}
