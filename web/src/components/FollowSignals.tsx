"use client";

import { useEffect, useState } from "react";
import { follow, getWatchlist, unfollow } from "@/lib/watchlist";
import { useSession } from "@/lib/session";

// One-tap follow toggles for a story's market signals (tickers + sector), shown
// inside the Markets lens block. Lives there because that lens is auth-gated, so
// every viewer here can follow. Reuses the watchlist API; toggles reflect on
// /watchlist. Normalizes to match the API's stored form (ticker upper, sector
// lower) so the "following" check lines up with getWatchlist().
export function FollowSignals({ tickers, sector }: { tickers: string[]; sector: string | null }) {
  const session = useSession();
  const [following, setFollowing] = useState<Set<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);

  useEffect(() => {
    if (!session) return;
    let cancelled = false;
    getWatchlist(session).then((items) => {
      if (!cancelled) setFollowing(new Set(items.map((it) => `${it.kind}:${it.value}`)));
    });
    return () => {
      cancelled = true;
    };
  }, [session]);

  if (!session) return null;

  const signals = [
    ...tickers.map((t) => ({ kind: "ticker", value: t.toUpperCase(), label: `$${t}` })),
    ...(sector ? [{ kind: "sector", value: sector.toLowerCase(), label: sector }] : []),
  ];
  if (signals.length === 0) return null;

  async function toggle(kind: string, value: string) {
    const key = `${kind}:${value}`;
    setBusy(key);
    try {
      const items = following.has(key) ? await unfollow(session!, kind, value) : await follow(session!, kind, value);
      setFollowing(new Set(items.map((it) => `${it.kind}:${it.value}`)));
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-1.5">
      <span className="text-[11px] font-semibold uppercase tracking-[0.14em]" style={{ color: "var(--ink-faint)" }}>
        Follow
      </span>
      {signals.map((s) => {
        const key = `${s.kind}:${s.value}`;
        const on = following.has(key);
        return (
          <button
            key={key}
            onClick={() => toggle(s.kind, s.value)}
            disabled={busy === key}
            aria-pressed={on}
            aria-label={`${on ? "Unfollow" : "Follow"} ${s.label}`}
            className="flex items-center gap-1 rounded-full border px-2.5 py-0.5 font-mono text-[11.5px] transition disabled:opacity-50"
            style={
              on
                ? { borderColor: "var(--lens-finance)", background: "var(--lens-finance-bg)", color: "var(--lens-finance)" }
                : { borderColor: "var(--line-strong)", color: "var(--ink-muted)" }
            }
          >
            <span aria-hidden>{on ? "✓" : "+"}</span>
            {s.label}
          </button>
        );
      })}
    </div>
  );
}
