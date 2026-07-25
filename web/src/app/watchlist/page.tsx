"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { type FormEvent, useCallback, useEffect, useState } from "react";

import { timeAgo } from "@/components/StoryCard";
import { useSession } from "@/lib/session";
import {
  follow,
  getWatchlist,
  unfollow,
  watchlistEvents,
  type WatchEvent,
  type WatchItem,
} from "@/lib/watchlist";

export default function WatchlistPage() {
  const session = useSession();
  const router = useRouter();
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

  if (!session) return null;

  return (
    <div className="mx-auto w-full max-w-[640px] px-8 pt-11 pb-24">
      <h1 className="text-[30px] font-semibold" style={{ fontFamily: "var(--font-display), serif" }}>
        Followed signals
      </h1>
      <p className="mt-2 text-[14px] leading-[1.6]" style={{ color: "var(--ink-muted)" }}>
        Follow tickers and sectors; their market-moving stories collect here when you open Parse.
      </p>

      <form onSubmit={add} className="mt-[22px] flex gap-2">
        <select
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          className="rounded-[10px] border px-3.5 py-2.5 text-[14px]"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
        >
          <option value="ticker">Ticker</option>
          <option value="sector">Sector</option>
        </select>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder={kind === "ticker" ? "e.g. RELIANCE" : "e.g. finance"}
          className="flex-1 rounded-[10px] border px-3.5 py-2.5 text-[14px] outline-none"
          style={{ borderColor: "var(--line-strong)", background: "var(--bg)", color: "var(--ink)" }}
        />
        <button
          type="submit"
          className="rounded-full px-5 py-2.5 text-[13px] font-semibold"
          style={{ background: "var(--ink)", color: "var(--bg)" }}
        >
          Follow
        </button>
      </form>

      {items.length > 0 && (
        <div className="mt-3.5 flex flex-wrap gap-2">
          {items.map((it) => (
            <span
              key={it.id}
              className="inline-flex items-center gap-1.5 rounded-full border px-3 py-1 font-mono text-[11.5px]"
              style={{ borderColor: "var(--line-strong)", color: "var(--ink)" }}
            >
              {it.kind === "sector" ? it.value : `$${it.value}`}
              <button onClick={() => remove(it)} aria-label={`Unfollow ${it.value}`} style={{ color: "var(--ink-faint)" }}>
                ✕
              </button>
            </span>
          ))}
        </div>
      )}

      <h2
        className="mt-9 text-[12px] font-semibold uppercase tracking-[0.14em]"
        style={{ color: "var(--ink-faint)" }}
      >
        Recent on your signals
      </h2>
      {ready && events.length === 0 ? (
        <p className="mt-2 text-[14px]" style={{ color: "var(--ink-muted)" }}>
          {items.length === 0
            ? "Follow a ticker or sector above to start seeing its stories."
            : "No recent stories on your followed signals yet."}
        </p>
      ) : (
        <div className="mt-2 flex flex-col">
          {events.map((ev) => {
            const isTicker = ev.tickers.length > 0;
            return (
              <Link
                key={ev.id}
                href={`/story/${ev.id}`}
                className="flex items-baseline gap-[14px] border-b py-3.5"
                style={{ borderColor: "var(--line)" }}
              >
                {isTicker ? (
                  <span
                    className="flex-none rounded-full px-[9px] py-0.5 font-mono text-[11px] font-semibold"
                    style={{ background: "var(--lens-finance-bg)", color: "var(--lens-finance)" }}
                  >
                    ${ev.tickers[0]}
                  </span>
                ) : ev.sector ? (
                  <span
                    className="flex-none rounded-full px-[9px] py-0.5 text-[11px] font-semibold"
                    style={{ background: "var(--bg-sunken)", color: "var(--ink-muted)" }}
                  >
                    {ev.sector}
                  </span>
                ) : null}
                <div className="min-w-0 flex-1">
                  <p className="text-[14px] font-semibold leading-[1.4]">{ev.title}</p>
                  <p className="mt-[3px] font-mono text-[10.5px]" style={{ color: "var(--ink-faint)" }}>
                    {timeAgo(ev.last_updated_at)}
                    {ev.catalyst && (
                      <>
                        {" · "}
                        <span style={{ color: "var(--up)" }}>▲ {ev.catalyst.replaceAll("_", " ")}</span>
                      </>
                    )}
                  </p>
                </div>
              </Link>
            );
          })}
        </div>
      )}
    </div>
  );
}
