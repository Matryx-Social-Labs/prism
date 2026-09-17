"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { ChartRow } from "@/components/ChartRow";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { fetchDigest, type MarketDigest } from "@/lib/api";
import { chartOrder } from "@/lib/chart";
import { istDate, istTime } from "@/lib/dateline";
import { useSession } from "@/lib/session";

/**
 * Market Pulse (shape brief §5): the day's markets digest as a dated chart
 * supplement. One column in the reading voice; every ticker it names in mono,
 * each opening that ticker's watchlist rows (or a search, for a reader with
 * no watchlist yet). Free, as before: the paid surface is the Markets lens on
 * a story. The markets lens IS speaking here, so its hue marks the supplement.
 */
const MONO = "font-mono text-[11px] uppercase tracking-[0.06em]";

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
  const stamp = digest?.generated_at ? `updated ${istTime(digest.generated_at)} IST` : null;
  const dateline = [istDate(new Date()), "Market pulse", stamp].filter(Boolean).join(" · ");

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 sm:px-8 lg:pb-16">
      <Masthead dateline={dateline} />

      {loading ? (
        <p className={`${MONO} rule-live mt-4 py-6`} style={{ color: "var(--ink-faint)" }}>Composing today&rsquo;s pulse…</p>
      ) : !digest ? (
        <p className="rule-live mt-4 py-6 text-[15px]" style={{ color: "var(--ink-muted)" }}>The market pulse isn&rsquo;t available right now.</p>
      ) : (
        <div className="max-w-[720px]">
          <h1 className="mt-4 text-[26px] font-medium leading-[1.2] text-balance sm:text-[30px]" style={{ color: "var(--ink)" }}>
            {digest.headline}
          </h1>
          {/* Provenance under the headline: the markets lens is speaking, so its hue marks the dot. */}
          <p className={`${MONO} mt-3 flex items-center gap-2`} style={{ color: "var(--lens-finance)" }}>
            <span aria-hidden className="inline-block h-[7px] w-[7px] rounded-full" style={{ background: "var(--lens-finance)" }} />
            Markets read
            <span style={{ color: "var(--ink-faint)" }}>· synthesized across {digest.event_ids.length} {digest.event_ids.length === 1 ? "story" : "stories"}</span>
          </p>
          <div className="mt-5 flex max-w-[62ch] flex-col gap-4">
            {digest.narrative.split(/\n{2,}/).map((para, i) => (
              <p key={i} className="text-[16px] leading-[1.7]" style={{ color: "var(--ink-muted)" }}>{para}</p>
            ))}
          </div>

          {/* The record under the reading: every story the digest was written
              from, as chart rows, so the page never shows a verdict alone. */}
          {(digest.stories?.length ?? 0) > 0 && (
            <section className="mt-10" aria-labelledby="from-title">
              <SectionHead id="from-title" title="Written from" count={digest.stories!.length} hint="The stories on the chart the pulse was synthesized across, most-corroborated first." />
              <ol>
                {chartOrder(digest.stories!).map((it) => (
                  <ChartRow key={it.id} item={it} />
                ))}
              </ol>
            </section>
          )}

          {digest.movers.length > 0 && (
            <section className="mt-10" aria-labelledby="movers-title">
              <SectionHead id="movers-title" title="Movers" count={digest.movers.length} />
              <ul>
                {digest.movers.map((m) => (
                  <li key={m.ticker} className="rule-live grid grid-cols-[96px_1fr] gap-x-4 py-3">
                    <Link href={tickerHref(m.ticker)} className="font-mono text-[12.5px] underline-offset-4 hover:underline" style={{ color: "var(--ink)" }}>
                      {m.ticker}
                    </Link>
                    <span className="text-[14.5px] leading-[1.55]" style={{ color: "var(--ink-muted)" }}>{m.note}</span>
                  </li>
                ))}
              </ul>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
