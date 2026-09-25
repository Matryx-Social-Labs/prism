"use client";

import { useEffect, useState } from "react";
import { ChartRow } from "@/components/ChartRow";
import { Masthead } from "@/components/Masthead";
import { PulseRail } from "@/components/reading/PulseRail";
import { SectionHead } from "@/components/SectionHead";
import { MarketDigest, MoversList } from "@/components/tabs/Markets";
import { EmptyState } from "@/components/ui";
import { fetchDigest, type MarketDigest as Digest } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { istTime } from "@/lib/dateline";
import { useSession } from "@/lib/session";

/**
 * Market Pulse (Design System v2 · Reading board, flow 03): the day's markets
 * reading in the Markets lens panel, the tickers it names with its one line on
 * each, and the Business & Markets stories it was written from, on the story
 * row grammar — so the page never shows a verdict alone. Beside it, the
 * reader's own tickers, or the way in. Never a price. Every ticker opens that
 * ticker's watchlist rows (or a search, for a reader with no account). Free:
 * the paid surface is the Markets lens on a story.
 */
export default function PulsePage() {
  const session = useSession();
  const [digest, setDigest] = useState<Digest | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDigest().then((d) => {
      setDigest(d);
      setLoading(false);
    });
  }, []);

  const tickerHref = (t: string) => (session ? `/watchlist?ticker=${encodeURIComponent(t)}` : `/search?q=${encodeURIComponent(t)}`);
  const stamp = digest?.generated_at ? `updated ${istTime(digest.generated_at)}` : null;
  const day = new Date().toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });
  const dateline = [day, stamp].filter(Boolean).join(" · ");
  const stories = digest?.stories ?? [];
  const n = digest?.event_ids.length ?? 0;
  const movers = digest?.movers ?? [];

  return (
    <div className="mx-auto max-w-[1020px] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:pb-16">
      <Masthead dateline={dateline} />
      <div className="grid gap-8 pt-4 lg:grid-cols-[minmax(0,640px)_340px] lg:justify-center lg:gap-10 lg:pt-8">
        <div className="grid min-w-0 grid-cols-[minmax(0,1fr)] content-start gap-6">
          <header className="grid gap-1.5">
            <h1 id="pulse-title" className="[font:var(--t-display-m)] lg:[font:var(--t-display-l)]" style={{ letterSpacing: "var(--track-display)" }}>Market Pulse</h1>
            <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
              What the day&rsquo;s business reporting says about markets and listed companies. Written from the reports; no prices, no advice.
            </p>
          </header>

          {loading ? (
            <div className="grid gap-3 p-5" aria-busy="true" aria-label="Loading the market pulse" style={{ background: "var(--lens-markets-soft)", borderTop: "3px solid var(--lens-markets)", borderRadius: "0 0 var(--r-lg) var(--r-lg)" }}>
              <span className="p-skel h-4 w-40" />
              <span className="p-skel h-6 w-[85%]" />
              <span className="p-skel h-3 w-full" />
              <span className="p-skel h-3 w-[70%]" />
            </div>
          ) : !digest ? (
            <EmptyState title="The market pulse isn’t available right now" />
          ) : (
            <>
              <MarketDigest digest={digest} full />

              <section aria-labelledby="movers-title">
                <SectionHead
                  id="movers-title"
                  title="Named in the reports"
                  sub={`${movers.length} ${movers.length === 1 ? "ticker" : "tickers"} · from ${n} ${n === 1 ? "story" : "stories"}`}
                />
                {movers.length > 0 ? (
                  <MoversList movers={movers} tickerHref={tickerHref} />
                ) : (
                  <p className="border-t pt-3" style={{ borderColor: "var(--line)", font: "var(--t-body-s)", color: "var(--ink-3)" }}>
                    Today&rsquo;s reading names no listed company.
                  </p>
                )}
              </section>

              {/* The record under the reading: every story the digest was written
                  from (the API selects them from business and finance). */}
              {stories.length > 0 && (
                <section aria-labelledby="from-title">
                  <SectionHead
                    id="from-title"
                    title="Business & Markets stories"
                    sub={`${stories.length} ${stories.length === 1 ? "record" : "records"}`}
                    hint="The stories the reading was written from, most-corroborated first."
                  />
                  <ol className="p-print mt-3 flex flex-col gap-3">
                    {chartOrder(stories).map((it) => (
                      <ChartRow key={it.id} item={it} />
                    ))}
                  </ol>
                </section>
              )}
            </>
          )}
        </div>
        <aside className="grid min-w-0 content-start gap-6 lg:sticky lg:top-[calc(var(--topbar)+24px)] lg:self-start" aria-label="Your tickers">
          <PulseRail session={session} named={digest ? movers.map((m) => m.ticker) : null} />
        </aside>
      </div>
    </div>
  );
}
