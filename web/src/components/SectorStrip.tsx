"use client";

import Link from "next/link";
import { NAV_ITEMS } from "@/lib/sectors";

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
    // Design System v2 · SubjectNav: chips on the phone, the "rail" variant from lg —
    // code | name | count on a 34px grid, the current subject in the accent tint.
    const cls = responsiveRail
      ? `chip lg:grid lg:min-h-10 lg:w-full lg:grid-cols-[34px_minmax(0,1fr)_auto] lg:gap-2 lg:whitespace-normal lg:rounded-[var(--r-md)] lg:border-0 lg:bg-transparent lg:px-2.5 lg:text-left lg:text-[14.5px] ${on ? "rail-on lg:font-semibold" : ""}`
      : "chip";
    const inner = (
      <>
        {responsiveRail && (
          <span className="hidden font-mono text-[10.5px] lg:inline" style={{ color: on ? "var(--accent)" : "var(--ink-3)" }}>
            {code}
          </span>
        )}
        <span>{name}</span>
        {n != null && (
          <span className={`p-chip__count ${responsiveRail ? `lg:opacity-100 ${on ? "lg:text-[color:var(--accent)]" : "lg:text-[color:var(--ink-3)]"}` : ""}`}>
            {n}
          </span>
        )}
      </>
    );
    const common = {
      className: cls,
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
          ? "hide-scroll -mx-[var(--gutter)] flex gap-2 overflow-x-auto px-[var(--gutter)] py-2.5 lg:mx-0 lg:grid lg:gap-px lg:overflow-visible lg:px-0 lg:py-0"
          : "hide-scroll -mx-[var(--gutter)] flex gap-2 overflow-x-auto px-[var(--gutter)] py-2.5"
      }
    >
      {item(null, "ALL", allLabel, allHref)}
      {NAV_ITEMS.map((n) => item(n.key, n.code, n.name, n.href))}
    </nav>
  );

  if (!responsiveRail) return navigation;

  return (
    <aside className="lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:self-start" aria-label="Browse by subject">
      {navigation}
      <div className="mt-5 hidden border-t px-2.5 pt-4 lg:block" style={{ borderColor: "var(--line)" }}>
        <p className="max-w-[22ch]" style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          One record per story, from monitored outlets. Every quote and source stays open.
        </p>
        <Link href="/about" className="p-link mt-2 inline-block text-[13.5px]">
          How Prism works →
        </Link>
      </div>
    </aside>
  );
}
