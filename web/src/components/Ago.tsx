"use client";

import { useSyncExternalStore } from "react";
import { istTime, relativeTime, shortDate } from "@/lib/dateline";

// Nothing to subscribe to: the age is read once per render, as before.
const subscribe = () => () => {};

/**
 * "12m ago" as a <time> — in the reader's browser. On the server it prints the
 * time itself, "27 Sept 10:00", because a cached page must be the same bytes
 * whenever it is rendered: Vercel skips the cache write only for identical
 * output, and an age printed on the server made every refresh of an unchanged
 * record a paid write (caching plan, 2026-09-27; components/deterministic.test).
 * A crawler or an answer engine is better served by the time than by an age
 * that was true when the page was cached. Hydration swaps it once; a
 * client-side navigation shows the age straight away.
 */
export function Ago({ iso, className, style }: { iso: string; className?: string; style?: React.CSSProperties }) {
  const text = useSyncExternalStore(
    subscribe,
    () => relativeTime(iso),
    () => `${shortDate(iso)} ${istTime(iso)}`,
  );
  return (
    <time dateTime={iso} className={className} style={style}>
      {text}
    </time>
  );
}
