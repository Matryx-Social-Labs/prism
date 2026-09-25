"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { SearchIcon } from "@/components/icons";
import { usePlan, useSession } from "@/lib/session";

// Destinations, in the reader's words. /trending stays the URL; "Stories" is
// what a reader calls the developing arcs (DESIGN.md decisions, 2026-09-18).
const NAV = [
  { href: "/feed", label: "Today" },
  { href: "/trending", label: "Stories" },
  { href: "/pulse", label: "Pulse" },
  { href: "/watchlist", label: "Watchlist" },
];

export function HeaderNav() {
  const pathname = usePathname();
  const router = useRouter();
  const session = useSession();
  const plan = usePlan(session);
  const searchRef = useRef<HTMLInputElement>(null);

  // `/` focuses the search field from anywhere the field is on screen, the way
  // a reader of any desktop news site expects; never while typing elsewhere.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "/" || e.metaKey || e.ctrlKey || e.altKey) return;
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) return;
      e.preventDefault();
      searchRef.current?.focus();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const landing = pathname === "/" || pathname === "/about";
  const active = (href: string) =>
    href === "/feed"
      ? ["/feed", "/sector"].some((p) => pathname === p || pathname.startsWith(`${p}/`))
      : pathname === href || pathname.startsWith(`${href}/`);

  return (
    <nav className="flex min-w-0 flex-1 items-center gap-5" aria-label="Primary">
      {!landing && (
        <div className="hidden items-center gap-0.5 lg:flex">
          {NAV.map((n) => {
            const on = active(n.href);
            return (
              <Link
                key={n.href}
                href={n.href}
                className="rounded-[var(--r-md)] px-3 py-2.5 text-[14.5px] font-semibold leading-none no-underline transition-colors"
                style={{ color: on ? "var(--ink)" : "var(--ink-2)", boxShadow: on ? "inset 0 -2px 0 var(--accent)" : "none" }}
                aria-current={on ? "page" : undefined}
              >
                {n.label}
              </Link>
            );
          })}
        </div>
      )}
      <span className="flex-1" />

      {/* A visible field, not an icon: search is a destination a first visitor
          should be able to see. The route owns the results; this only carries
          the query there. */}
      {!landing && (
        <form
          role="search"
          className="hidden h-10 w-[300px] min-w-0 items-center gap-2.5 rounded-[var(--r-md)] border pl-3 pr-2.5 lg:flex"
          style={{ borderColor: "var(--line-strong)", background: "var(--surface)", color: "var(--ink-3)" }}
          onSubmit={(e) => {
            e.preventDefault();
            const q = searchRef.current?.value.trim();
            if (q) router.push(`/search?q=${encodeURIComponent(q)}`);
          }}
        >
          <SearchIcon size={16} />
          <input
            ref={searchRef}
            name="q"
            type="search"
            placeholder="Search stories, people, places"
            aria-label="Search"
            className="w-full min-w-0 bg-transparent text-[14.5px] outline-none placeholder:text-[var(--ink-3)]"
            style={{ color: "var(--ink)" }}
          />
          <kbd className="p-kbd">/</kbd>
        </form>
      )}

      <div className="flex shrink-0 items-center gap-2">
        {plan !== "plus" && !landing && (
          <Link href="/plus?from=header" className="hidden text-[14.5px] font-semibold no-underline sm:inline" style={{ color: "var(--accent)" }}>Plus</Link>
        )}
        <ThemeToggle />
        {landing ? (
          <Link href="/feed" className="btn btn-primary btn-sm"><span className="lg:hidden">Today&rsquo;s record</span><span className="hidden lg:inline">Open today&rsquo;s record</span></Link>
        ) : session ? (
          <Link
            href="/account"
            className="flex h-[34px] w-[34px] items-center justify-center rounded-full text-[12px] font-semibold uppercase no-underline"
            style={{ background: "var(--ink)", color: "var(--paper)" }}
            title={`Signed in as ${session.email}`}
            aria-label={`Account for ${session.email}`}
          >
            {session.email.slice(0, 1)}
          </Link>
        ) : (
          <Link href="/signin" className="btn btn-secondary btn-sm">Sign in</Link>
        )}
      </div>
    </nav>
  );
}
