"use client";

import Link from "next/link";
import { useEffect, useRef } from "react";
import type { StripDay } from "@/lib/archive";

/**
 * Today, yesterday and the days before (lib/archive.dayStrip) as the system's
 * tab row (.sc-tabs): a day's label over its count of records from two or more
 * outlets, the day being read marked, a day Prism was not reading listed but
 * not linked. Not prefetched: a strip on every view of Today would render seven
 * day pages per reader (the grievance lesson, 2026-11-02).
 */
export function DayStrip({ days }: { days: StripDay[] }) {
  const ref = useRef<HTMLElement>(null);
  // The day being read can sit off a phone's edge; bring it in once, without motion.
  useEffect(() => {
    ref.current?.querySelector<HTMLElement>('[aria-current="page"]')?.scrollIntoView?.({ block: "nearest", inline: "center", behavior: "instant" });
  }, []);
  return (
    <nav ref={ref} aria-label="Days" className="sc-tabs sc-days">
      {days.map((d) =>
        d.href ? (
          <Link
            key={d.date}
            href={d.href}
            prefetch={false}
            aria-current={d.current ? "page" : undefined}
            aria-label={d.count != null ? `${d.label}, ${d.count} ${d.count === 1 ? "record" : "records"} from two or more outlets` : d.label}
          >
            <span>{d.label}</span>
            {d.count != null && <span className="p-count">{d.count}</span>}
          </Link>
        ) : (
          <span key={d.date} className="sc-days__off" title="Prism was not reading this day">
            <span>{d.label}</span>
            <span className="p-count">not read</span>
          </span>
        ),
      )}
      <Link href="/archive" prefetch={false} className="sc-days__all">
        All days →
      </Link>
    </nav>
  );
}
