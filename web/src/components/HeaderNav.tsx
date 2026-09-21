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
    <nav className="flex min-w-0 items-center justify-end gap-2 lg:grid lg:grid-cols-[minmax(0,auto)_minmax(240px,1fr)_auto] lg:gap-5" aria-label="Primary">
      <div className="hidden items-center gap-0.5 lg:flex">
        {NAV.map((n) => {
          const on = active(n.href);
          return (
            <Link
              key={n.href}
              href={n.href}
              className="nav-link px-3 py-2 text-[14px] font-medium transition-colors"
              style={{
                color: on ? "var(--accent)" : "var(--ink-2)",
                background: on ? "var(--accent-soft)" : "transparent",
              }}
              aria-current={on ? "page" : undefined}
            >
              {n.label}
            </Link>
          );
        })}
      </div>

      {/* A visible field, not an icon: search is a destination a first visitor
          should be able to see (DESIGN.md § Navigation). The route owns the
          results; this only carries the query there. */}
      <form
        role="search"
        className="search-entry mx-auto hidden h-[38px] w-full max-w-[440px] min-w-0 items-center gap-2 border px-3 text-[14px] lg:flex"
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
          className="w-full bg-transparent text-[14px] outline-none placeholder:text-[var(--ink-3)]"
          style={{ color: "var(--ink)" }}
        />
        <kbd className="rounded border px-1.5 font-mono text-[11px]" style={{ borderColor: "var(--line)", color: "var(--ink-3)" }}>/</kbd>
      </form>

      <div className="flex shrink-0 items-center gap-1.5">
        {plan !== "plus" && !landing && (
          <Link href="/plus?from=header" className="btn btn-ghost hidden sm:inline-flex" style={{ color: "var(--ink-2)" }}>Plus</Link>
        )}
        <ThemeToggle />
        {session ? (
          <Link
            href="/account"
            className="flex h-9 w-9 items-center justify-center rounded-full text-[13px] font-semibold uppercase"
            style={{ background: "var(--accent-soft)", color: "var(--accent)" }}
            title={`Signed in as ${session.email}`}
            aria-label={`Account for ${session.email}`}
          >
            {session.email.slice(0, 1)}
          </Link>
        ) : landing ? (
          <>
            <Link href="/signin" className="btn btn-ghost hidden sm:inline-flex">Sign in</Link>
            <Link href="/feed" className="btn btn-primary">Open today&rsquo;s record</Link>
          </>
        ) : (
          <Link href="/signin" className="btn btn-ghost">Sign in</Link>
        )}
      </div>
    </nav>
  );
}
