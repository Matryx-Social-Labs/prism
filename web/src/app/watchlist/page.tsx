"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { istDate, shortDate } from "@/lib/dateline";
import { sectorCode } from "@/lib/sectors";
import { useSession } from "@/lib/session";
import { follow, getWatchlist, unfollow, watchlistEvents, type WatchEvent, type WatchItem } from "@/lib/watchlist";

/**
 * Watchlist (shape brief §7): a chart of the reader's followed tickers and
 * sectors. Rows are stories that mention them, the ticker in mono at the left
 * where the chart keeps its sources count. Empty: the form to follow one.
 * `?ticker=X` (from Market Pulse) narrows the rows to one ticker.
 */
const MONO = "font-mono text-[11px] uppercase tracking-[0.06em]";

function WatchlistInner() {
  const session = useSession();
  const router = useRouter();
  const only = useSearchParams().get("ticker");
  const [items, setItems] = useState<WatchItem[]>([]);
  const [events, setEvents] = useState<WatchEvent[]>([]);
  const [kind, setKind] = useState("ticker");
  const [value, setValue] = useState("");
  const [ready, setReady] = useState(false);

  const refresh = useCallback(async () => {
    if (!session) return;
    const [list, evs] = await Promise.all([getWatchlist(session), watchlistEvents(session)]);
    setItems(list);
    setEvents(evs);
    setReady(true);
  }, [session]);

  // Redirect to sign-in only once we've confirmed there's no session in storage.
  useEffect(() => {
    const t = setTimeout(() => {
      if (!localStorage.getItem("prism.session.v1")) router.replace("/signin");
    }, 0);
    return () => clearTimeout(t);
  }, [router]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  async function add(e: FormEvent) {
    e.preventDefault();
    if (!session || !value.trim()) return;
    setItems(await follow(session, kind, value.trim()));
    setValue("");
    setEvents(await watchlistEvents(session));
  }

  async function remove(it: WatchItem) {
    if (!session) return;
    setItems(await unfollow(session, it.kind, it.value));
    setEvents(await watchlistEvents(session));
  }

  const rows = useMemo(() => (only ? events.filter((e) => e.tickers.includes(only)) : events), [events, only]);

  if (!session) return null;

  const dateline = `${istDate(new Date())} · ${items.length} followed`;

  return (
    <div className="mx-auto max-w-[1240px] px-5 pb-24 sm:px-8 lg:pb-16">
      <Masthead dateline={dateline} />
      <h1 className="pt-4 font-display text-[26px] uppercase leading-none tracking-[0.03em]">Watchlist</h1>

      {items.length > 0 && (
        <ul className="mt-4 flex flex-wrap gap-2">
          {items.map((it) => (
            <li key={it.id} className="inline-flex items-center gap-2 border px-3 py-1.5 font-mono text-[12px]" style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}>
              {it.value}
              <button onClick={() => remove(it)} aria-label={`Unfollow ${it.value}`} style={{ color: "var(--ink-faint)" }}>✕</button>
            </li>
          ))}
        </ul>
      )}

      <form onSubmit={add} className="rule-live mt-4 flex flex-wrap gap-2 py-4">
        <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="What to follow"
          className="h-12 border px-3 text-[15px]" style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", color: "var(--ink)" }}>
          <option value="ticker">Ticker</option>
          <option value="sector">Sector</option>
        </select>
        <input value={value} onChange={(e) => setValue(e.target.value)} aria-label={kind === "ticker" ? "Ticker" : "Sector"}
          placeholder={kind === "ticker" ? "e.g. RELIANCE" : "e.g. finance"}
          className="h-12 min-w-0 flex-1 border px-4 text-[15px] outline-none" style={{ borderColor: "var(--line-strong)", background: "var(--bg-elevated)", color: "var(--ink)" }} />
        <button type="submit" className="rounded-full px-5 text-[14px] font-semibold" style={{ background: "var(--ink)", color: "var(--bg)" }}>Follow</button>
      </form>

      <section className="mt-6" aria-labelledby="rows-title">
        <SectionHead id="rows-title" title={only ? `On ${only}` : "On your signals"} count={ready ? rows.length : undefined} />
        {only && (
          <Link href="/watchlist" className={`${MONO} mb-3 inline-block underline-offset-4 hover:underline`} style={{ color: "var(--ink-muted)" }}>All signals →</Link>
        )}
        {ready && rows.length === 0 ? (
          <p className="text-[15px]" style={{ color: "var(--ink-muted)" }}>
            {items.length === 0 ? "Follow a ticker or sector above and its stories collect here." : only ? `No recent stories mention ${only}.` : "No recent stories on your signals yet."}
          </p>
        ) : (
          <ol className="chart-print">
            {rows.map((ev) => {
              const mark = ev.tickers[0] ?? (ev.sector ? sectorCode(ev.sector) : "");
              const grid = [shortDate(ev.last_updated_at), sectorCode(ev.sector) || null, ev.catalyst?.replaceAll("_", " ") ?? null].filter((x): x is string => Boolean(x));
              return (
                <li key={ev.id} className="rule-live">
                  <Link href={`/story/${ev.id}`} className="group grid grid-cols-[88px_1fr] gap-x-4 py-3.5">
                    <span className="truncate font-mono text-[12px] leading-[1.9]" style={{ color: "var(--ink)" }}>{mark}</span>
                    <span className="min-w-0">
                      <span className="block text-[15.5px] font-medium leading-[1.4] group-hover:underline underline-offset-4" style={{ color: "var(--ink)" }}>{ev.title}</span>
                      <span className={`${MONO} mt-1.5 flex flex-wrap gap-x-2.5`} style={{ color: "var(--ink-faint)" }}>
                        {grid.map((g) => <span key={g}>{g}</span>)}
                      </span>
                    </span>
                  </Link>
                </li>
              );
            })}
          </ol>
        )}
      </section>
    </div>
  );
}

export default function WatchlistPage() {
  return (
    <Suspense fallback={null}>
      <WatchlistInner />
    </Suspense>
  );
}
