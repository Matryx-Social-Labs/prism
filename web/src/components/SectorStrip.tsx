"use client";

import Link from "next/link";
import { SECTOR_GROUPS } from "@/lib/sectors";

/**
 * The subject nav, on every surface. Six codes, like the station codes on a
 * reservation chart; the full name on desktop. Sticky under the masthead.
 *
 * This is the fix for "I can't get to my sector": a reader never has to know a
 * URL or scroll to a band heading. `active` underlines the current one; ALL is
 * the front page. On the feed the parent re-sorts the chart in place when a
 * code is chosen (see Chart.tsx); elsewhere the codes are plain links.
 */
export function SectorStrip({
  active,
  onPick,
  allHref = "/feed",
  allLabel = "Today",
  responsiveRail = false,
}: {
  active: string | null;
  /** When present, codes call this instead of navigating — the chart re-sorts in place. */
  onPick?: (slug: string | null) => void;
  allHref?: string;
  /** The subject beside the ALL code: Today on the chart; empty where ALL needs no name. */
  allLabel?: string;
  /** Use the same accessible nav as a horizontal strip on small screens and a left rail on desktop. */
  responsiveRail?: boolean;
}) {
  const item = (slug: string | null, code: string, name: string, href: string) => {
    const on = active === slug;
    const cls = responsiveRail
      ? "group flex h-11 shrink-0 items-end gap-1 border-b-2 px-2 pb-2 pt-3 leading-none transition-colors lg:grid lg:h-auto lg:min-h-[44px] lg:w-full lg:grid-cols-[34px_1fr] lg:items-center lg:gap-2 lg:border-b-0 lg:border-l-2 lg:px-3 lg:py-0 lg:text-left"
      : "flex h-11 shrink-0 items-end gap-1 border-b-2 px-2 pb-2 pt-3 leading-none transition-[border-color]";
    const style = {
      borderColor: on ? "var(--ink)" : "transparent",
      background: responsiveRail && on ? "var(--bg-sunken)" : "transparent",
    };
    const inner = (
      <>
        <span
          className="font-mono text-[12px] tracking-[0.06em]"
          style={{ color: on ? "var(--ink)" : "var(--ink-muted)" }}
        >
          {code}
        </span>
        {(name || responsiveRail) && (
          <span
            className={`${name ? "hidden sm:inline" : "hidden"} text-[13.5px] font-medium lg:inline lg:leading-[1.25] group-hover:underline group-focus-visible:underline lg:underline-offset-4`}
            style={{ color: on ? "var(--ink)" : "var(--ink-muted)" }}
          >
            {name || "All stories"}
          </span>
        )}
      </>
    );
    return onPick ? (
      <button
        key={code}
        type="button"
        onClick={() => onPick(slug)}
        className={cls}
        style={style}
        aria-current={on ? "page" : undefined}
      >
        {inner}
      </button>
    ) : (
      <Link key={code} href={href} className={cls} style={style} aria-current={on ? "page" : undefined}>
        {inner}
      </Link>
    );
  };

  const navigation = (
    <nav
      aria-label="Sectors"
      className={responsiveRail
        ? "hide-scroll flex items-stretch gap-1 overflow-x-auto border-b sm:gap-3 lg:flex-col lg:gap-0.5 lg:overflow-visible lg:border-b-0"
        : "hide-scroll sticky top-0 z-20 flex items-stretch gap-1 overflow-x-auto border-b sm:gap-3 lg:top-[57px]"}
      style={{ borderColor: "var(--line)", background: "var(--bg)" }}
    >
      {item(null, "ALL", allLabel, allHref)}
      {SECTOR_GROUPS.map((g) => item(g.slug, g.code, g.name, `/sector/${g.slug}`))}
    </nav>
  );

  if (!responsiveRail) return navigation;

  return (
    <aside
      className="sticky top-0 z-20 self-start border-b lg:top-[81px] lg:z-0 lg:border-b-0 lg:border-r lg:pr-5"
      style={{ borderColor: "var(--line)", background: "var(--bg)" }}
      aria-label="Browse by subject"
    >
      <p className="hidden pb-3 font-display text-[20px] uppercase leading-none tracking-[0.04em] lg:block">Browse</p>
      {navigation}
      <div className="mt-7 hidden border-t pt-4 lg:block" style={{ borderColor: "var(--line)" }}>
        <p className="max-w-[19ch] text-[12.5px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>
          One live record from monitored outlets. Sources stay open for inspection.
        </p>
        <Link
          href="/about"
          className="mt-3 inline-block font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline"
          style={{ color: "var(--ink)" }}
        >
          How Prism works
        </Link>
      </div>
    </aside>
  );
}
