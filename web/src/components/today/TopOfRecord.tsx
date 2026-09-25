"use client";

import { useState } from "react";
import type { FeedItem } from "@/lib/api";
import { StoryCard } from "@/components/StoryCard";

const CARD = 272;
const STEP = CARD + 12; // card + the .sc-rail gap

/**
 * Top of the record (phone, Pages v3 · Today): the day's multi-outlet stories as
 * a card rail, "k / n" and a dot pager that follow the scroll. Hidden from lg,
 * where the chart's lead row does this job.
 */
export function TopOfRecord({ stories }: { stories: FeedItem[] }) {
  const [at, setAt] = useState(0);
  if (!stories.length) return null;
  return (
    <section aria-labelledby="top-of-record" className="pt-2.5 lg:hidden">
      <div className="flex items-baseline gap-2">
        <h2 id="top-of-record" className="flex-1" style={{ font: "var(--t-title)" }}>Top of the record</h2>
        <span className="p-count">{at + 1} / {stories.length}</span>
      </div>
      <div className="sc-rail mt-2.5" onScroll={(e) => setAt(Math.min(stories.length - 1, Math.round(e.currentTarget.scrollLeft / STEP)))}>
        {stories.map((s) => <StoryCard key={s.id} item={s} width={CARD} />)}
      </div>
      <div className="mt-1 flex justify-center gap-1" aria-hidden>
        {stories.map((s, i) => (
          <i key={s.id} style={{ width: i === at ? 16 : 5, height: 5, background: i === at ? "var(--ink)" : "var(--line-strong)", transition: "width 240ms var(--ease)" }} />
        ))}
      </div>
    </section>
  );
}
