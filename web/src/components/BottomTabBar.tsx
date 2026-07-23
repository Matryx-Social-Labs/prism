"use client";

// Mobile-only bottom tab bar (v2). App-like navigation on the core browsing
// routes; hidden on desktop (lg+) and on marketing/flow routes where it would
// get in the way (landing, onboarding, story detail — which docks its own Ask
// pill — and auth/account screens).
import Link from "next/link";
import { usePathname } from "next/navigation";

const TABS = [
  { href: "/feed", label: "Feed", glyph: "◮" },
  { href: "/trending", label: "Trending", glyph: "▲" },
  { href: "/pulse", label: "Pulse", glyph: "◉" },
  { href: "/search", label: "Search", glyph: "⌕" },
  { href: "/watchlist", label: "Watchlist", glyph: "◇" },
];

// Route prefixes where the tab bar is shown.
const SHOW_ON = ["/feed", "/trending", "/pulse", "/search", "/watchlist", "/sector"];

export function BottomTabBar() {
  const pathname = usePathname();
  if (!SHOW_ON.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return null;

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 flex border-t px-2 pb-[env(safe-area-inset-bottom)] pt-2.5 backdrop-blur-md lg:hidden"
      style={{ borderColor: "var(--line)", background: "var(--glass)" }}
      aria-label="Primary"
    >
      {TABS.map((t) => {
        const active = pathname === t.href || pathname.startsWith(`${t.href}/`);
        return (
          <Link
            key={t.href}
            href={t.href}
            className="flex flex-1 flex-col items-center gap-0.5 pb-1 text-[10.5px] font-semibold"
            style={{ color: active ? "var(--ink)" : "var(--ink-faint)" }}
          >
            <span aria-hidden className="text-[15px] leading-none">
              {t.glyph}
            </span>
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
