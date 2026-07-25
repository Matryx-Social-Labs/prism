"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { fetchDigest, type MarketDigest } from "@/lib/api";

function updatedLabel(iso: string | null): string {
  if (!iso) return "";
  const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const h = Math.floor(mins / 60);
  return h < 24 ? `${h}h ago` : `${Math.floor(h / 24)}d ago`;
}

export default function PulsePage() {
  const [digest, setDigest] = useState<MarketDigest | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchDigest().then((d) => {
      setDigest(d);
      setLoading(false);
    });
  }, []);

  return (
    <div className="mx-auto w-full max-w-[720px] px-5 pb-28 pt-10">
      <div className="flex items-center gap-2">
        <span className="h-[9px] w-[9px] rounded-full" style={{ background: "var(--lens-finance)" }} aria-hidden />
        <span className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--lens-finance)" }}>
          Market Pulse
        </span>
      </div>

      {loading ? (
        <p className="mt-6 text-[14px]" style={{ color: "var(--ink-faint)" }}>
          Composing today&apos;s market pulse…
        </p>
      ) : !digest ? (
        <p className="mt-6 text-[14px]" style={{ color: "var(--ink-muted)" }}>
          The market pulse isn&apos;t available right now.
        </p>
      ) : (
        <>
          <h1 className="mt-3 text-[30px] font-semibold leading-[1.15]" style={{ fontFamily: "var(--font-display), serif" }}>
            {digest.headline}
          </h1>
          {digest.generated_at && (
            <p className="mt-2 font-mono text-[11px]" style={{ color: "var(--ink-faint)" }}>
              Updated {updatedLabel(digest.generated_at)} · synthesized across {digest.event_ids.length} stories
            </p>
          )}

          <div className="mt-6 flex flex-col gap-4">
            {digest.narrative.split(/\n{2,}/).map((para, i) => (
              <p key={i} className="text-[15px] leading-[1.7]" style={{ color: "var(--ink-muted)" }}>
                {para}
              </p>
            ))}
          </div>

          {digest.movers.length > 0 && (
            <section className="mt-9">
              <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
                Movers
              </h2>
              <ul className="mt-3 flex flex-col divide-y" style={{ borderColor: "var(--line)" }}>
                {digest.movers.map((m) => (
                  <li key={m.ticker} className="flex items-baseline gap-3 py-2.5">
                    <Link
                      href={`/search?q=${encodeURIComponent(m.ticker)}`}
                      className="shrink-0 rounded-full px-2 py-0.5 font-mono text-[12px] font-medium"
                      style={{ background: "var(--lens-finance-bg)", color: "var(--lens-finance)" }}
                    >
                      ${m.ticker}
                    </Link>
                    <span className="text-[13.5px] leading-[1.5]" style={{ color: "var(--ink-muted)" }}>
                      {m.note}
                    </span>
                  </li>
                ))}
              </ul>
            </section>
          )}

          <Link href="/feed" className="mt-9 inline-block text-[13px]" style={{ color: "var(--ink-faint)" }}>
            ← Back to your feed
          </Link>
        </>
      )}
    </div>
  );
}
