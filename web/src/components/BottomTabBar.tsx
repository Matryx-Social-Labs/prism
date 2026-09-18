"use client";

// The phone's navigation spine — the future app's tab bar. Today · Stories ·
// Search · Watchlist · You (founder call 2026-09-18; Pulse became a module on
// Today and keeps its route). Hidden on desktop (lg+) and on surfaces that pin
// their own thumb-zone controls (the story record, onboarding, auth).
import Link from "next/link";
import { usePathname } from "next/navigation";
import { SearchIcon, StoriesIcon, TodayIcon, WatchlistIcon, YouIcon } from "@/components/icons";

type Tab = { href: string; label: string; Icon: (p: { size?: number }) => React.ReactNode };

const TABS: Tab[] = [
  { href: "/feed", label: "Today", Icon: TodayIcon },
  { href: "/trending", label: "Stories", Icon: StoriesIcon },
  { href: "/search", label: "Search", Icon: SearchIcon },
  { href: "/watchlist", label: "Watchlist", Icon: WatchlistIcon },
  { href: "/you", label: "You", Icon: YouIcon },
];

// Routes that fold into a tab: the You hub, and the chart under Today. Pulse
// lives under Watchlist on the phone (a markets reader's home).
const YOU_ROUTES = ["/you", "/account", "/interests"];
const TODAY_ROUTES = ["/feed", "/sector"];
const WATCH_ROUTES = ["/watchlist", "/pulse"];
const SHOW_ON = ["/trending", "/search", ...TODAY_ROUTES, ...YOU_ROUTES, ...WATCH_ROUTES];

export function BottomTabBar() {
  const pathname = usePathname();
  const under = (prefixes: string[]) => prefixes.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (!under(SHOW_ON)) return null;

  const isActive = (href: string) => {
    if (href === "/feed") return under(TODAY_ROUTES);
    if (href === "/you") return under(YOU_ROUTES);
    if (href === "/watchlist") return under(WATCH_ROUTES);
    return under([href]);
  };

  return (
    <nav
      className="glass fixed inset-x-0 bottom-0 z-40 grid grid-cols-5 border-t lg:hidden"
      style={{
        borderColor: "var(--line)",
        height: "calc(var(--tabbar) + env(safe-area-inset-bottom))",
        paddingBottom: "env(safe-area-inset-bottom)",
      }}
      aria-label="Primary"
    >
      {TABS.map(({ href, label, Icon }) => {
        const active = isActive(href);
        return (
          <Link
            key={href}
            href={href}
            aria-current={active ? "page" : undefined}
            className="flex touch-manipulation flex-col items-center justify-center gap-[3px] text-[11px] transition-opacity active:opacity-65"
            style={{ color: active ? "var(--accent)" : "var(--ink-3)", fontWeight: active ? 600 : 500 }}
          >
            <Icon />
            {label}
            <span aria-hidden className="mt-px h-[2px] w-4 rounded-full" style={{ background: active ? "var(--accent)" : "transparent" }} />
          </Link>
        );
      })}
    </nav>
  );
}
