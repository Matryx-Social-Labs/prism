"use client";

// Mobile bottom tab bar (mobile-first design). The app's navigation spine on the
// phone: Feed · Trending · Pulse · Search · You. Hidden on desktop (lg+) and on
// surfaces with their own thumb-zone controls (landing, onboarding, story detail —
// which pins a lens rail + Share/Ask — and auth).
import Link from "next/link";
import { usePathname } from "next/navigation";

type Tab = { href: string; label: string; icon: React.ReactNode };

const I = (d: React.ReactNode) => (
  <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
    {d}
  </svg>
);

const TABS: Tab[] = [
  { href: "/feed", label: "Feed", icon: I(<path d="M4 5h16M4 12h16M4 19h10" />) },
  { href: "/trending", label: "Trending", icon: I(<><path d="M3 17l6-6 4 4 8-8" /><path d="M14 7h7v7" /></>) },
  { href: "/pulse", label: "Pulse", icon: I(<path d="M3 12h4l3-7 4 14 3-7h4" />) },
  { href: "/search", label: "Search", icon: I(<><circle cx="11" cy="11" r="7" /><path d="M21 21l-4.3-4.3" /></>) },
  { href: "/you", label: "You", icon: I(<><circle cx="12" cy="8" r="4" /><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6" /></>) },
];

// Routes that fold into the "You" hub — the You tab stays active across them.
const YOU_ROUTES = ["/you", "/account", "/interests", "/watchlist"];
// Route prefixes where the tab bar is shown (story detail is excluded — it pins
// its own lens rail + Share/Ask in the thumb zone).
const SHOW_ON = ["/feed", "/trending", "/pulse", "/search", "/sector", ...YOU_ROUTES];

export function BottomTabBar() {
  const pathname = usePathname();
  if (!SHOW_ON.some((p) => pathname === p || pathname.startsWith(`${p}/`))) return null;

  const isActive = (href: string) => {
    if (href === "/you") return YOU_ROUTES.some((p) => pathname === p || pathname.startsWith(`${p}/`));
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t backdrop-blur-md lg:hidden"
      style={{
        borderColor: "var(--line)",
        background: "var(--glass)",
        paddingTop: 7,
        paddingBottom: "max(1.75rem, env(safe-area-inset-bottom))",
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
            className="flex min-h-[44px] flex-col items-center justify-center gap-[3px] text-[10px]"
            style={{ color: active ? "var(--ink)" : "var(--ink-faint)", fontWeight: active ? 600 : 500 }}
          >
            <span aria-hidden>{t.icon}</span>
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
