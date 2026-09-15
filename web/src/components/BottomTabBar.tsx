"use client";

// Mobile bottom tab bar (mobile-first design). The app's navigation spine on the
// phone: Today · Trending · Pulse · Search · You (founder decision D6). Hidden on
// desktop (lg+) and on surfaces with their own thumb-zone controls (onboarding,
// story detail — which pins a lens rail + Share/Ask — and auth).
import Link from "next/link";
import { usePathname } from "next/navigation";

type Tab = { href: string; label: string; icon: React.ReactNode };

const I = (d: React.ReactNode) => (
  <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    {d}
  </svg>
);

const TABS: Tab[] = [
  { href: "/", label: "Today", icon: I(<path d="M4 5h16M4 12h16M4 19h10" />) },
  { href: "/trending", label: "Trending", icon: I(<><path d="M3 17l6-6 4 4 8-8" /><path d="M14 7h7v7" /></>) },
  { href: "/pulse", label: "Pulse", icon: I(<path d="M3 12h4l3-7 4 14 3-7h4" />) },
  { href: "/search", label: "Search", icon: I(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>) },
  { href: "/you", label: "You", icon: I(<><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></>) },
];

// Routes that fold into the "You" hub — the You tab stays active across them.
const YOU_ROUTES = ["/you", "/account", "/interests", "/watchlist"];
// The chart is / and /feed, and a sector is the chart filtered — all Today.
const TODAY_ROUTES = ["/feed", "/sector"];
// Route prefixes where the tab bar is shown (story detail is excluded — it pins
// its own lens rail + Share/Ask in the thumb zone).
const SHOW_ON = ["/trending", "/pulse", "/search", ...TODAY_ROUTES, ...YOU_ROUTES];

export function BottomTabBar() {
  const pathname = usePathname();
  const under = (prefixes: string[]) => prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (pathname !== "/" && !under(SHOW_ON)) return null;

  const isActive = (href: string) => {
    if (href === "/") return pathname === "/" || under(TODAY_ROUTES);
    if (href === "/you") return under(YOU_ROUTES);
    return under([href]);
  };

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t lg:hidden"
      style={{
        borderColor: "var(--line)",
        background: "var(--bg)",
        paddingTop: 6,
        paddingBottom: "calc(env(safe-area-inset-bottom) + 6px)",
      }}
      aria-label="Primary"
    >
      {TABS.map((t) => {
        const active = isActive(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            aria-current={active ? "page" : undefined}
            // --ink-faint at 10px measures 2.57:1 on light — under WCAG AA (4.5:1)
            // for the app's primary navigation. --ink-muted is 5.28:1, and weight
            // plus full-strength ink still carry the active state.
            className="flex min-h-[44px] flex-col items-center justify-center gap-[3px] text-[11px]"
            style={{ color: active ? "var(--ink)" : "var(--ink-muted)", fontWeight: active ? 600 : 500 }}
          >
            <span aria-hidden>{t.icon}</span>
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
