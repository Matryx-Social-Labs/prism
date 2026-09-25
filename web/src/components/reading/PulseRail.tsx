"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { TickerChip } from "@/components/tabs/Markets";
import type { Session } from "@/lib/session";
import { follow, getWatchlist, unfollow } from "@/lib/watchlist";

/**
 * Market Pulse's rail (Reading board, flow 03): the reader's own tickers, each
 * with its Following toggle, and which of them today's reading does not name;
 * signed out, what following does and the way in. Only what the watchlist API
 * returns: a ticker unfollowed here stays listed (as "Follow") until the page
 * is left, so a slip can be undone in place.
 */
export function PulseRail({ session, named }: { session: Session | null; named: string[] | null }) {
  return (
    <section aria-labelledby="tickers-title" className="grid content-start gap-2.5">
      <h2 id="tickers-title" className="p-eyebrow pb-2" style={{ borderBottom: "var(--rule-section) solid var(--ink)" }}>Your tickers</h2>
      {session ? (
        <Followed session={session} named={named} />
      ) : (
        <>
          <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>Follow a ticker to see its stories on your watchlist. Free with an account.</p>
          <Link href="/signin?next=/pulse" className="p-btn p-btn--secondary p-btn--block">Sign in</Link>
        </>
      )}
    </section>
  );
}

function Followed({ session, named }: { session: Session; named: string[] | null }) {
  const [tickers, setTickers] = useState<string[] | null>(null);
  const [on, setOn] = useState<ReadonlySet<string>>(new Set());
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    getWatchlist(session)
      .then((items) => {
        if (cancelled) return;
        const t = items.filter((i) => i.kind === "ticker").map((i) => i.value);
        setTickers(t);
        setOn(new Set(t));
      })
      .catch(() => { if (!cancelled) setError("Your watchlist did not load. Reload to try again."); });
    return () => { cancelled = true; };
  }, [session]);

  const toggle = async (t: string) => {
    const was = on.has(t);
    setBusy(t);
    setError(null);
    try {
      const items = await (was ? unfollow(session, "ticker", t) : follow(session, "ticker", t));
      setOn(new Set(items.filter((i) => i.kind === "ticker").map((i) => i.value)));
    } catch {
      setError(was ? `Could not stop following ${t}. Try again.` : `Could not follow ${t}. Try again.`);
    } finally {
      setBusy(null);
    }
  };

  if (error && tickers === null) return <p role="alert" style={{ font: "var(--t-body-s)", color: "var(--danger)" }}>{error}</p>;
  if (tickers === null) return <div aria-busy="true" className="grid gap-2"><span className="p-skel h-8 w-40" /><span className="p-skel h-8 w-32" /></div>;
  if (tickers.length === 0) {
    return (
      <>
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>You follow no tickers yet. Add one on your watchlist to see its stories there.</p>
        <Link href="/watchlist" className="p-link inline-flex min-h-11 items-center text-[14px]">Your watchlist →</Link>
      </>
    );
  }
  const unnamed = named ? tickers.filter((t) => on.has(t) && !named.includes(t)) : [];
  return (
    <>
      <ul className="grid gap-2">
        {tickers.map((t) => (
          <li key={t}><TickerChip symbol={t} href={`/watchlist?ticker=${encodeURIComponent(t)}`} following={on.has(t)} onToggle={() => toggle(t)} busy={busy === t} /></li>
        ))}
      </ul>
      {error && <p role="alert" style={{ font: "var(--t-body-s)", color: "var(--danger)" }}>{error}</p>}
      {unnamed.length > 0 && (
        <p style={{ font: "var(--t-body-s)", color: "var(--ink-3)" }}>
          {unnamed.join(", ")} {unnamed.length === 1 ? "is" : "are"} not named in today&rsquo;s reading.
        </p>
      )}
      <Link href="/watchlist" className="p-link inline-flex min-h-11 items-center text-[14px]">Your watchlist →</Link>
    </>
  );
}
