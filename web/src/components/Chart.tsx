"use client";

import Link from "next/link";
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
  emptyLabel,
  yesterdayHref,
}: {
  items: FeedItem[];
  primaryLang?: string;
  /** What to say when the chart has no rows — names the subject, offers yesterday. */
  emptyLabel: string;
  yesterdayHref?: string;
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
    return (
      <div className="rule-live py-8">
        <p className="text-[15px]" style={{ color: "var(--ink-muted)" }}>
          {emptyLabel}
          {yesterdayHref && (
            <>
              {" · "}
              <Link href={yesterdayHref} className="underline underline-offset-4" style={{ color: "var(--ink)" }}>
                yesterday&rsquo;s chart →
              </Link>
            </>
          )}
        </p>
      </div>
    );
  }

  return (
    <div>
      <ol
        className="chart-print"
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
          />
        ))}
      </ol>
      {yesterdayHref && (
        <div className="rule-live mt-2 py-5">
          <Link
            href={yesterdayHref}
            className="font-mono text-[11px] uppercase tracking-[0.06em] underline-offset-4 hover:underline"
            style={{ color: "var(--ink-muted)" }}
          >
            Yesterday&rsquo;s chart →
          </Link>
        </div>
      )}
    </div>
  );
}