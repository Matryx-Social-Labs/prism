"use client";

import { useEffect, useState } from "react";
import type { FeedItem } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { ChartRow } from "@/components/ChartRow";

export { chartOrder } from "@/lib/chart";

const LAST_OPENED = "prism.chart.lastOpened";

export function rememberOpened(id: string) {
  try {
    window.localStorage.setItem(LAST_OPENED, id);
  } catch {
    /* private mode: the mark is a courtesy, not a contract */
  }
}

export function Chart({
  items,
  primaryLang = "en",
  pageCode = null,
  emptyLabel,
}: {
  items: FeedItem[];
  primaryLang?: string;
  /** The sector code the page is filtered to; rows omit it. */
  pageCode?: string | null;
  /** What to say when the chart has no rows — names the subject. */
  emptyLabel: string;
}) {
  const ordered = chartOrder(items);
  const [lastOpened, setLastOpened] = useState<string | null>(null);
  useEffect(() => {
    try {
      setLastOpened(window.localStorage.getItem(LAST_OPENED));
    } catch {
      /* ignore */
    }
  }, []);

  if (ordered.length === 0) {
    // Design System v2 · EmptyState: a dashed box, the title names what is missing.
    return (
      <div className="px-5 py-8" style={{ border: "1px dashed var(--line-strong)", borderRadius: "var(--r-lg)" }}>
        <p style={{ font: "var(--t-title-s)" }}>{emptyLabel}</p>
      </div>
    );
  }

  // One column on the phone; two from sm, the lead spanning both (ChartRow's
  // `sm:col-span-2`). Rows print in (.p-print).
  return (
    <div>
      <ol
        className="p-print grid grid-cols-1 gap-3 sm:grid-cols-2"
        onClickCapture={(e) => {
          const a = (e.target as HTMLElement).closest("a[href^='/story/']");
          const id = a?.getAttribute("href")?.split("/story/")[1];
          if (id) rememberOpened(id);
        }}
      >
        {ordered.map((it, i) => (
          <ChartRow
            key={it.id}
            item={it}
            lead={i === 0}
            lastOpened={it.id === lastOpened}
            primaryLang={primaryLang}
            pageCode={pageCode}
          />
        ))}
      </ol>
    </div>
  );
}