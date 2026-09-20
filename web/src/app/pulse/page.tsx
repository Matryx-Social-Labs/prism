"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChartRow } from "@/components/ChartRow";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { fetchDigest, type MarketDigest } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { istTime } from "@/lib/dateline";
import { useSession } from "@/lib/session";

/**
 * Market Pulse: the day's markets digest as a reading with its record under
 * it — every story it was written from, on the story row grammar. Every ticker
 * opens that ticker's watchlist rows (or a search, for a reader with no
 * watchlist yet). Free: the paid surface is the Markets lens on a story. The
 * markets lens IS speaking here, so its hue marks the reading.
 */

export default function PulsePage() {
  const session = useSession();
  const [digest, setDigest] = useState<MarketDigest | null>(null);
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

  return (
    <div className="mx-auto max-w-[var(--shell)] px-5 pb-[calc(var(--tabbar)+24px)] sm:px-8 lg:pb-16 xl:px-10">
      <Masthead dateline={dateline} />
      <div className="mx-auto max-w-[720px] lg:pt-6">
        <SectionHead id="pulse-title" title="Market Pulse" hint="One reading of the day's market-moving stories, written from the record beneath it." right={<Link href="/watchlist" className="btn btn-secondary btn-sm">Watchlist</Link>} />

        {loading ? (
          <div className="card" aria-busy="true"><span className="pulse-skel block h-4 w-3/4 rounded" style={{ background: "var(--sunken)" }} /><span className="pulse-skel mt-3 block h-3 w-full rounded" style={{ background: "var(--sunken)" }} /><span className="pulse-skel mt-2 block h-3 w-5/6 rounded" style={{ background: "var(--sunken)" }} /></div>
        ) : !digest ? (
          <div className="card py-8 text-center"><p className="text-[15px]" style={{ color: "var(--ink-2)" }}>The market pulse isn&rsquo;t available right now.</p></div>
        ) : (
          <div>
            <article className="card p-5 sm:p-6" style={{ borderTop: "3px solid var(--lens-markets)" }}>
              <p className="lensdot l-markets"><i /> Markets read <span className="font-mono text-[11px] font-normal" style={{ color: "var(--ink-3)" }}>· written from {digest.event_ids.length} {digest.event_ids.length === 1 ? "story" : "stories"}{stamp ? ` · ${stamp}` : ""}</span></p>
              <h1 className="font-record mt-3 text-[26px] font-medium leading-[1.2] text-balance sm:text-[30px]" style={{ color: "var(--ink)", letterSpacing: "-0.01em" }}>
                {digest.headline}
              </h1>
              <div className="mt-4 flex max-w-[64ch] flex-col gap-4">
                {digest.narrative.split(/\n{2,}/).map((para, i) => (
                  <p key={i} className="text-[16px] leading-[1.7]" style={{ color: "var(--ink-2)" }}>{para}</p>
                ))}
              </div>
            </article>

            {digest.movers.length > 0 && (
              <section className="mt-8" aria-labelledby="movers-title">
                <SectionHead id="movers-title" title="Movers" count={digest.movers.length} />
                <ul className="card divide-y p-0" style={{ borderColor: "var(--line)" }}>
                  {digest.movers.map((m) => (
                    <li key={m.ticker} className="grid grid-cols-[104px_1fr] gap-x-4 px-4 py-3" style={{ borderColor: "var(--line)" }}>
                      <Link href={tickerHref(m.ticker)} className="chip h-7 self-start px-2.5 font-mono text-[11.5px] l-markets" style={{ borderColor: "var(--lens-markets-soft)", background: "var(--lens-markets-soft)" }}>
                        {m.ticker}
                      </Link>
                      <span className="text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-2)" }}>{m.note}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {/* The record under the reading: every story the digest was written
                from, so the page never shows a verdict alone. */}
            {(digest.stories?.length ?? 0) > 0 && (
              <section className="mt-8" aria-labelledby="from-title">
                <SectionHead id="from-title" title="Written from" count={digest.stories!.length} hint="The stories the pulse was written from, most-corroborated first." />
                <ol className="flex flex-col gap-3">
                  {chartOrder(digest.stories!).map((it) => (
                    <ChartRow key={it.id} item={it} />
                  ))}
                </ol>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
