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
}: {
  active: string | null;
  /** When present, codes call this instead of navigating — the chart re-sorts in place. */
  onPick?: (slug: string | null) => void;
  allHref?: string;
  /** What ALL means on this surface: Today on the chart, All on a chart of arcs or results. */
  allLabel?: string;
}) {
  const item = (slug: string | null, code: string, name: string, href: string) => {
    const on = active === slug;
    const cls =
      "flex h-11 shrink-0 items-end gap-1 px-2 pb-2 pt-3 leading-none border-b-2 transition-[border-color]";
    const style = { borderColor: on ? "var(--ink)" : "transparent" };
    const inner = (
      <>
        <span
          className="font-mono text-[12px] tracking-[0.06em]"
          style={{ color: on ? "var(--ink)" : "var(--ink-muted)" }}
        >
          {code}
        </span>
        <span
          className="hidden text-[13.5px] font-medium sm:inline"
          style={{ color: on ? "var(--ink)" : "var(--ink-muted)" }}
        >
          {name}
        </span>
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

  return (
    <nav
      aria-label="Sectors"
      className="hide-scroll sticky top-0 z-20 flex items-stretch gap-1 overflow-x-auto border-b sm:gap-3 lg:top-[57px]"
      style={{ borderColor: "var(--line)", background: "var(--bg)" }}
    >
      {item(null, "ALL", allLabel, allHref)}
      {SECTOR_GROUPS.map((g) => item(g.slug, g.code, g.name, `/sector/${g.slug}`))}
    </nav>
  );
}
