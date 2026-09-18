"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { Close } from "@/components/icons";
import { relativeTime } from "@/lib/dateline";
import { sectorGroup } from "@/lib/sectors";
import { useSession } from "@/lib/session";
import { follow, getWatchlist, unfollow, watchlistEvents, type WatchEvent, type WatchItem } from "@/lib/watchlist";

/**
 * Watchlist: the reader's followed tickers and sectors, and the stories that
 * touch them on the story row grammar. Empty: the form to follow one.
 * `?ticker=X` (from Market Pulse) narrows the rows to one ticker. Pulse is
 * linked from here on the phone, where it has no tab of its own.
 */
const SHELL = "mx-auto max-w-[var(--reading)] px-5 pb-[calc(var(--tabbar)+24px)] sm:px-8 lg:max-w-[880px] lg:pb-16";
const today = () => new Date().toLocaleDateString("en-IN", { weekday: "short", day: "numeric", month: "short", timeZone: "Asia/Kolkata" });

function WatchlistInner() {
  const session = useSession();
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

  // Signed out: the page stays and says what it is, the way the ticket gates
  // a locked lens — never a bounce to /signin with no context. Decided once
  // storage has been read, so a signed-in reader never sees the gate flash.
  const [signedOut, setSignedOut] = useState(false);
  useEffect(() => {
    const t = setTimeout(() => setSignedOut(!localStorage.getItem("prism.session.v1")), 0);
    return () => clearTimeout(t);
  }, [session]);

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

  if (!session) {
    if (!signedOut) return null;
    return (
      <div className={SHELL}>
        <Masthead dateline={today()} />
        <SectionHead id="watch-title" title="Watchlist" hint="Follow tickers and sectors, and the stories that touch them line up here. Free with an account." />
        <div className="card flex flex-col items-start gap-4">
          <p className="text-[15px] leading-[1.6]" style={{ color: "var(--ink-2)" }}>Sign in to follow a ticker or a sector. Your list stays yours; the stories come from the same record everyone reads.</p>
          <Link href="/signin?next=/watchlist" className="btn btn-primary">Sign in</Link>
        </div>
      </div>
    );
  }

  const dateline = `${today()} · ${items.length} followed`;

  return (
    <div className={SHELL}>
      <Masthead dateline={dateline} />
      <div className="lg:pt-6">
        <SectionHead
          id="watch-title"
          title="Watchlist"
          hint={items.length ? `${items.length} followed · stories that mention them, newest first` : "Follow a ticker or a sector to start."}
          right={<Link href="/pulse" className="btn btn-secondary btn-sm">Market Pulse</Link>}
        />

        <form onSubmit={add} className="card flex flex-wrap items-center gap-2">
          <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="What to follow"
            className="h-11 rounded-full border px-3 text-[15px]" style={{ borderColor: "var(--line-strong)", background: "var(--surface)", color: "var(--ink)" }}>
            <option value="ticker">Ticker</option>
            <option value="sector">Sector</option>
          </select>
          <input value={value} onChange={(e) => setValue(e.target.value)} aria-label={kind === "ticker" ? "Ticker" : "Sector"}
            placeholder={kind === "ticker" ? "e.g. RELIANCE" : "e.g. finance"}
            className="h-11 min-w-0 flex-1 rounded-full border px-4 text-[16px] outline-none" style={{ borderColor: "var(--line-strong)", background: "var(--surface)", color: "var(--ink)" }} />
          <button type="submit" className="btn btn-primary">Follow</button>
          {items.length > 0 && (
            <ul className="mt-1 flex w-full flex-wrap gap-2 border-t pt-3" style={{ borderColor: "var(--line)" }}>
              {items.map((it) => (
                <li key={it.id} className="chip h-8 gap-1 pr-1 font-mono text-[12px]">
                  {it.value}
                  <button onClick={() => remove(it)} aria-label={`Unfollow ${it.value}`} className="icon-btn h-7 w-7" style={{ color: "var(--ink-3)" }}>
                    <Close />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </form>

        <section className="mt-6" aria-labelledby="rows-title">
          <SectionHead id="rows-title" title={only ? `On ${only}` : "On your signals"} count={ready ? rows.length : undefined}
            right={only ? <Link href="/watchlist" className="btn btn-ghost btn-sm">All signals</Link> : undefined} />
          {ready && rows.length === 0 ? (
            <div className="card py-8 text-center"><p className="text-[15px]" style={{ color: "var(--ink-2)" }}>
              {items.length === 0 ? "Follow a ticker or sector above and its stories collect here." : only ? `No recent stories mention ${only}.` : "No recent stories on your signals yet."}
            </p></div>
          ) : (
            <ol className="chart-print flex flex-col gap-3">
              {rows.map((ev) => {
                const g = sectorGroup(ev.sector);
                return (
                  <li key={ev.id}>
                    <Link href={`/story/${ev.id}`} className="row-card group px-4 py-3.5">
                      <div className="meta-line">
                        {g && <span style={{ color: "var(--ink-2)", fontWeight: 500 }}>{g.name}</span>}
                        {g && <span className="dot" />}
                        <span>{relativeTime(ev.last_updated_at)}</span>
                        {ev.catalyst && (<><span className="dot" /><span>{ev.catalyst.replaceAll("_", " ")}</span></>)}
                      </div>
                      <h2 className="font-record mt-1.5 text-[19px] font-medium leading-[1.3] group-hover:underline underline-offset-4 decoration-1" style={{ color: "var(--ink)" }}>{ev.title}</h2>
                      {ev.tickers.length > 0 && (
                        <div className="mt-2.5 flex flex-wrap gap-1.5">
                          {ev.tickers.slice(0, 4).map((t) => (
                            <span key={t} className="chip h-7 px-2.5 font-mono text-[11.5px] l-markets" style={{ borderColor: "var(--lens-markets-soft)", background: "var(--lens-markets-soft)" }}>{t}</span>
                          ))}
                        </div>
                      )}
                    </Link>
                  </li>
                );
              })}
            </ol>
          )}
        </section>
      </div>
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
