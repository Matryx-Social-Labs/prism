"use client";

import Link from "next/link";
import { SECTOR_GROUPS } from "@/lib/sectors";

/**
 * The subject nav, on every list surface. Six subjects and All; pill chips in
 * a scrolling rail on the phone, the left rail on desktop — one DOM, restyled
 * by breakpoint, so there is one accessible control. On the chart a chip
 * re-sorts the list in place (see Chart.tsx); elsewhere it links.
 */
export function SectorStrip({
  active,
  onPick,
  allHref = "/feed",
  allLabel = "All stories",
  responsiveRail = false,
  counts,
}: {
  active: string | null;
  /** When present, chips call this instead of navigating — the chart re-sorts in place. */
  onPick?: (slug: string | null) => void;
  allHref?: string;
  allLabel?: string;
  /** Rail on desktop, chips on the phone (default: chips everywhere). */
  responsiveRail?: boolean;
  /** Stories per subject on the current page, printed after the name. */
  counts?: Record<string, number>;
}) {
  const item = (slug: string | null, code: string, name: string, href: string) => {
    const on = active === slug;
    const n = counts?.[slug ?? "all"];
    const cls = responsiveRail
      ? "chip lg:flex lg:h-10 lg:w-full lg:justify-start lg:gap-2.5 lg:rounded-[var(--r-md)] lg:border-0 lg:bg-transparent lg:px-3 lg:text-[14.5px]"
      : "chip";
    const inner = (
      <>
        {responsiveRail && (
          <span className="hidden w-7 font-mono text-[11px] tracking-[0.04em] lg:inline" style={{ color: on ? "var(--accent)" : "var(--ink-3)" }}>
            {code}
          </span>
        )}
        <span>{name}</span>
        {n != null && (
          <span className="font-mono text-[11px] opacity-70 lg:ml-auto lg:opacity-100" style={responsiveRail ? { color: "var(--ink-3)" } : undefined}>
            {n}
          </span>
        )}
      </>
    );
    const common = {
      className: `${cls} ${responsiveRail && on ? "rail-on" : ""}`,
      "aria-current": on ? ("page" as const) : undefined,
    };
    return onPick ? (
      <button key={code} type="button" onClick={() => onPick(slug)} {...common}>
        {inner}
      </button>
    ) : (
      <Link key={code} href={href} {...common}>
        {inner}
      </Link>
    );
  };

  const navigation = (
    <nav
      aria-label="Subjects"
      className={
        responsiveRail
          ? "hide-scroll -mx-5 flex gap-2 overflow-x-auto px-5 py-2.5 sm:-mx-8 sm:px-8 lg:mx-0 lg:flex-col lg:gap-0.5 lg:overflow-visible lg:px-0 lg:py-0"
          : "hide-scroll -mx-5 flex gap-2 overflow-x-auto px-5 py-2.5 sm:-mx-8 sm:px-8"
      }
    >
      {item(null, "ALL", allLabel, allHref)}
      {SECTOR_GROUPS.map((g) => item(g.slug, g.code, g.name, `/sector/${g.slug}`))}
    </nav>
  );

  if (!responsiveRail) return navigation;

  return (
    <aside className="lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:self-start" aria-label="Browse by subject">
      {navigation}
      <div className="mt-5 hidden border-t pt-4 lg:block" style={{ borderColor: "var(--line)" }}>
        <p className="max-w-[22ch] text-[13px] leading-[1.5]" style={{ color: "var(--ink-3)" }}>
          One record per story, from monitored outlets. Every quote and source stays open.
        </p>
        <Link href="/about" className="mt-2 inline-block text-[13.5px] font-semibold hover:underline underline-offset-4" style={{ color: "var(--accent)" }}>
          How Prism works →
        </Link>
      </div>
    </aside>
  );
}
