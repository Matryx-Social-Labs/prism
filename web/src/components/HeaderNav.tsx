"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { lensMeta } from "@/lib/lenses";
import { loadProfile } from "@/lib/profile";
import { useSession } from "@/lib/session";

export function HeaderNav() {
  const pathname = usePathname();
  const [lens, setLens] = useState<string | null>(null);
  const session = useSession();

  useEffect(() => {
    setLens(loadProfile()?.lens ?? null);
  }, [pathname]);

  const m = lens ? lensMeta(lens) : null;

  return (
    <nav className="flex items-center gap-2">
      <Link
        href="/feed"
        className="px-2 py-1.5 text-[13.5px] font-medium"
        style={{ color: pathname === "/feed" ? "var(--ink)" : "var(--ink-muted)" }}
      >
        Feed
      </Link>
      <Link
        href="/pulse"
        className="px-2 py-1.5 text-[13.5px] font-medium"
        style={{ color: pathname === "/pulse" ? "var(--ink)" : "var(--ink-muted)" }}
      >
        Pulse
      </Link>
      <Link
        href="/about"
        className="hidden px-2 py-1.5 text-[13.5px] font-medium sm:block"
        style={{ color: pathname === "/about" ? "var(--ink)" : "var(--ink-muted)" }}
      >
        About
      </Link>
      <Link
        href="/search"
        aria-label="Search"
        className="flex h-8 w-8 items-center justify-center rounded-full"
        style={{ color: pathname === "/search" ? "var(--ink)" : "var(--ink-muted)" }}
      >
        <svg aria-hidden width="16" height="16" viewBox="0 0 24 24" fill="none">
          <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
          <path d="M20 20l-3.5-3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </Link>
      {session && (
        <Link
          href="/watchlist"
          className="px-2 py-1.5 text-[13.5px] font-medium"
          style={{ color: pathname === "/watchlist" ? "var(--ink)" : "var(--ink-muted)" }}
        >
          Watchlist
        </Link>
      )}
      {m && (
        <Link
          href="/interests"
          className="flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-semibold"
          style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
          title="Your region, lens, and interests"
        >
          <span className="h-[7px] w-[7px] rounded-full" style={{ background: m.color }} />
          {m.short}
        </Link>
      )}
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
          href="/signin"
          className="px-2 py-1.5 text-[13.5px] font-medium"
          style={{ color: pathname === "/signin" ? "var(--ink)" : "var(--ink-muted)" }}
        >
          Sign in
        </Link>
      )}
      <ThemeToggle />
    </nav>
  );
}
