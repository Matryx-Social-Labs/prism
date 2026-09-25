"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { Close } from "@/components/icons";
import { EmptyState } from "@/components/tabs/EmptyState";
import { MarketDigest, MoversList, TickerChip } from "@/components/tabs/Markets";
import { fetchDigest, type MarketDigest as Digest } from "@/lib/api";
import { sectorGroup } from "@/lib/sectors";
import { useSession } from "@/lib/session";
import { follow, getWatchlist, unfollow, watchlistEvents, type WatchEvent, type WatchItem } from "@/lib/watchlist";
import { Ago } from "@/components/Ago";

/**
 * Watchlist (Design System v2 · reader-phone Watchlist): the reader's followed
 * tickers and sectors, the day's markets reading when the API has written one,
 * and the stories that touch what they follow, on the story row grammar.
 * `?ticker=X` (from Market Pulse) narrows the rows to one ticker. Pulse is
 * linked from here on the phone, where it has no tab of its own.
 */
const SHELL = "mx-auto max-w-[var(--reading)] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:max-w-[880px] lg:pb-12";
const tickerHref = (t: string) => `/watchlist?ticker=${encodeURIComponent(t)}`;

function WatchlistInner() {
  const session = useSession();
  const only = useSearchParams().get("ticker");
  const [items, setItems] = useState<WatchItem[]>([]);
  const [events, setEvents] = useState<WatchEvent[]>([]);
  const [digest, setDigest] = useState<Digest | null>(null);
  const [kind, setKind] = useState("ticker");
  const [value, setValue] = useState("");
  const [ready, setReady] = useState(false);
  // A failed call says so; it used to be an unhandled rejection and a list
  // that simply never arrived.
  const [problem, setProblem] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!session) return;
    try {
      const [list, evs] = await Promise.all([getWatchlist(session), watchlistEvents(session)]);
      setItems(list);
      setEvents(evs);
      setProblem(null);
    } catch {
      setProblem("Your watchlist could not be loaded. Check your connection and reload.");
    } finally {
      setReady(true);
    }
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

  // The markets reading is public (it is Market Pulse's); shown only when the
  // API has one — fetchDigest resolves null on a 204 or an outage.
  useEffect(() => {
    if (session) fetchDigest().then(setDigest);
  }, [session]);

  async function add(e: FormEvent) {
    e.preventDefault();
    const v = value.trim();
    if (!session || !v) return;
    try {
      setItems(await follow(session, kind, v));
      setValue("");
      setEvents(await watchlistEvents(session));
      setProblem(null);
    } catch {
      setProblem(`Could not follow ${v}. Try again.`);
    }
  }

  async function remove(it: WatchItem) {
    if (!session) return;
    try {
      setItems(await unfollow(session, it.kind, it.value));
      setEvents(await watchlistEvents(session));
      setProblem(null);
    } catch {
      setProblem(`Could not unfollow ${it.value}. Try again.`);
    }
  }

  const rows = useMemo(() => (only ? events.filter((e) => e.tickers.includes(only)) : events), [events, only]);

  if (!session) {
    if (!signedOut) return null;
    return (
      <div className={SHELL}>
        <Masthead dateline="Watchlist" />
        <div className="grid gap-3 pt-4 lg:pt-6">
          <SectionHead id="watch-title" as="h1" title="Watchlist" hint="Follow tickers and sectors, and the stories that touch them line up here. Free with an account." />
          <EmptyState title="Sign in to follow a ticker or a sector" action={<Link href="/signin?next=/watchlist" className="p-btn p-btn--primary">Sign in</Link>}>
            Your list stays yours; the stories come from the same record everyone reads.
          </EmptyState>
        </div>
      </div>
    );
  }

  return (
    <div className={SHELL}>
      <Masthead dateline="Watchlist" />
      <div className="grid gap-3 pt-4 lg:pt-6">
        <SectionHead
          id="watch-title"
          as="h1"
          title="Watchlist"
          sub={ready ? `${items.length} followed` : undefined}
          right={<Link href="/pulse" className="p-link inline-flex min-h-11 items-center text-[13.5px]">Market Pulse →</Link>}
        />

        {problem && <div className="p-alert p-alert--error" role="status"><p>{problem}</p></div>}

        {digest && !only && (
          <div>
            <MarketDigest digest={digest} />
            {digest.movers.length > 0 && <div className="mt-3"><MoversList movers={digest.movers} tickerHref={tickerHref} /></div>}
          </div>
        )}

        <form onSubmit={add} className="mt-2 grid gap-3 border-t pt-4" style={{ borderColor: "var(--line)" }} aria-label="Follow a ticker or a sector">
          <div className="flex flex-wrap gap-2">
            <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="What to follow" className="p-input" style={{ width: "auto" }}>
              <option value="ticker">Ticker</option>
              <option value="sector">Sector</option>
            </select>
            <input
              value={value}
              onChange={(e) => setValue(e.target.value)}
              aria-label={kind === "ticker" ? "Ticker" : "Sector"}
              placeholder={kind === "ticker" ? "e.g. RELIANCE" : "e.g. finance"}
              className="p-input min-w-0 flex-1 basis-40"
            />
            <button type="submit" className="p-btn p-btn--primary">Follow</button>
          </div>
          {items.length > 0 && (
            <ul className="flex flex-wrap items-center gap-x-1 gap-y-2" aria-label="Following">
              {items.map((it) => (
                <li key={it.id} className="inline-flex items-center">
                  {it.kind === "ticker" ? <TickerChip symbol={it.value} href={tickerHref(it.value)} /> : <span className="p-chip">{sectorGroup(it.value)?.name ?? it.value}</span>}
                  <button type="button" onClick={() => remove(it)} aria-label={`Unfollow ${it.value}`} className="p-iconbtn">
                    <Close />
                  </button>
                </li>
              ))}
            </ul>
          )}
        </form>

        <section className="mt-4" aria-labelledby="rows-title">
          <SectionHead
            id="rows-title"
            title={only ? `On ${only}` : "On your signals"}
            count={ready ? rows.length : undefined}
            right={only ? <Link href="/watchlist" className="p-btn p-btn--ghost p-btn--sm">All signals</Link> : undefined}
          />
          {ready && rows.length === 0 ? (
            <EmptyState title={items.length === 0 ? "Nothing followed yet" : only ? `No recent stories mention ${only}` : "No recent stories on your signals yet"}>
              {items.length === 0 ? "Follow a ticker or sector above and its stories collect here." : null}
            </EmptyState>
          ) : (
            <ol className="p-print grid gap-2.5">
              {rows.map((ev) => <WatchRow key={ev.id} ev={ev} />)}
            </ol>
          )}
        </section>
      </div>
    </div>
  );
}

/** A story on the reader's signals, on the story row grammar: meta, title, what
 *  changed, and the tickers it touches in the foot. */
function WatchRow({ ev }: { ev: WatchEvent }) {
  const g = sectorGroup(ev.sector);
  const meta: React.ReactNode[] = [];
  if (g) meta.push(<span key="s" className="p-meta__subject">{g.name}</span>);
  meta.push(<Ago key="t" iso={ev.last_updated_at} className="p-meta__prov" />);
  if (ev.catalyst) meta.push(<span key="c" style={{ font: "500 12.5px/1.3 var(--font-read)" }}>{ev.catalyst.replaceAll("_", " ")}</span>);
  return (
    <li>
      <Link href={`/story/${ev.id}`} className="p-row" style={{ padding: "14px 16px 12px", gap: 8 }}>
        <div className="p-meta">{meta.flatMap((m, i) => (i ? [<span key={`d${i}`} className="p-meta__sep" />, m] : [m]))}</div>
        <h2 className="p-row__title">{ev.title}</h2>
        {ev.summary && <p className="p-row__sum">{ev.summary}</p>}
        {ev.tickers.length > 0 && (
          <div className="p-row__foot">
            {ev.tickers.slice(0, 4).map((t) => <TickerChip key={t} symbol={t} />)}
          </div>
        )}
      </Link>
    </li>
  );
}

export default function WatchlistPage() {
  return (
    <Suspense fallback={null}>
      <WatchlistInner />
    </Suspense>
  );
}
