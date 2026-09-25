"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense, type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { Masthead } from "@/components/Masthead";
import { SectionHead } from "@/components/SectionHead";
import { Close } from "@/components/icons";
import { Alert, EmptyState, SelectField, TextField } from "@/components/ui";
import { SignalRow, SubjectChip, splitFollows, tickerHref, type FollowedSubject } from "@/components/accounts/signals";
import { MarketDigest, MoversList, TickerChip } from "@/components/tabs/Markets";
import { fetchDigest, type MarketDigest as Digest } from "@/lib/api";
import { shortDate } from "@/lib/dateline";
import { SECTOR_GROUPS } from "@/lib/sectors";
import { useSession } from "@/lib/session";
import { follow, getWatchlist, unfollow, watchlistEvents, type WatchEvent, type WatchItem } from "@/lib/watchlist";

/**
 * Watchlist (Design System v2 · Accounts board, flow 05): the reader's followed
 * tickers and subjects as chips with a remove control, the day's markets reading
 * when the API has written one, and the stories on those signals — today's first,
 * then earlier ones. `?ticker=X` (from Market Pulse or a chip) narrows the rows
 * to one ticker. No prices, ever. Free with an account (the API has no plan gate).
 */
const SHELL = "mx-auto max-w-[var(--reading)] px-[var(--gutter)] pb-[calc(var(--tabbar)+24px)] lg:max-w-[760px] lg:pb-12";
const TITLE = "text-balance [font:var(--t-display-m)] lg:[font:var(--t-display-l)]";
// NSE symbols are letters, digits and & - . (M&M, BAJAJ-AUTO); BSE codes are six digits.
const SYMBOL = /^[A-Z0-9&.-]{1,20}$/;

/** The IST calendar day of an instant: "today" on this page means since midnight IST. */
const istDay = (d: Date) => d.toLocaleDateString("en-CA", { timeZone: "Asia/Kolkata" });

function symbolProblem(v: string, following: readonly string[]): string | null {
  if (!v) return "Type a symbol, like RELIANCE.";
  if (!SYMBOL.test(v)) return "A symbol is letters and numbers, like RELIANCE or M&M, or a six-digit BSE code.";
  if (following.includes(v)) return `You already follow ${v}.`;
  return null;
}

function WatchlistInner() {
  const session = useSession();
  const only = useSearchParams().get("ticker");
  const [items, setItems] = useState<WatchItem[]>([]);
  const [events, setEvents] = useState<WatchEvent[]>([]);
  const [digest, setDigest] = useState<Digest | null>(null);
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

  // Every write returns the whole list; the stories follow what is now followed.
  async function apply(write: () => Promise<WatchItem[]>, failure: string) {
    if (!session) return false;
    try {
      setItems(await write());
      setEvents(await watchlistEvents(session));
      setProblem(null);
      return true;
    } catch {
      setProblem(failure);
      return false;
    }
  }

  const { tickers, subjects } = useMemo(() => splitFollows(items), [items]);
  const followed = tickers.length + subjects.length;
  const today = istDay(new Date());
  const scoped = only ? events.filter((e) => e.tickers.includes(only)) : events;
  const todays = scoped.filter((e) => istDay(new Date(e.last_updated_at)) === today);
  const earlier = scoped.filter((e) => istDay(new Date(e.last_updated_at)) !== today);

  if (!session) return signedOut ? <SignedOut /> : null;

  const filterChips = [...new Set([...tickers.map((t) => t.value), ...(only ? [only] : [])])];
  const names = [...tickers.map((t) => t.value), ...subjects.map((s) => s.name)];

  return (
    <div className={SHELL}>
      <Masthead dateline="Watchlist" />
      <div className="grid gap-[22px] pt-4 lg:pt-9">
        <div className="grid gap-1">
          <h1 className={TITLE} style={{ letterSpacing: "var(--track-display)" }}>Watchlist</h1>
          <div className="flex flex-wrap items-baseline gap-x-2.5">
            {ready && <span className="p-count">{followed} FOLLOWED</span>}
            <Link href="/pulse" className="p-link inline-flex min-h-11 items-center text-[13.5px]">Market Pulse →</Link>
          </div>
        </div>

        {problem && <Alert tone="error">{problem}</Alert>}

        {digest && !only && (
          <div>
            <MarketDigest digest={digest} />
            {digest.movers.length > 0 && <div className="mt-3"><MoversList movers={digest.movers} tickerHref={tickerHref} /></div>}
          </div>
        )}

        <FollowForm
          following={tickers.map((t) => t.value)}
          subjects={subjects.map((s) => s.key)}
          onTicker={(v) => apply(() => follow(session, "ticker", v), `Could not follow ${v}. Try again.`)}
          onSubject={(sectors, name) =>
            apply(async () => {
              let list: WatchItem[] = [];
              for (const s of sectors) list = await follow(session, "sector", s);
              return list;
            }, `Could not follow ${name}. Try again.`)
          }
        />

        {followed > 0 && (
          <ul className="flex flex-wrap items-center gap-x-1 gap-y-2" aria-label="Following">
            {tickers.map((it) => (
              <li key={it.id} className="inline-flex items-center">
                <TickerChip symbol={it.value} href={tickerHref(it.value)} />
                <RemoveButton label={it.value} onClick={() => apply(() => unfollow(session, it.kind, it.value), `Could not stop following ${it.value}. Try again.`)} />
              </li>
            ))}
            {subjects.map((s: FollowedSubject) => (
              <li key={s.key} className="inline-flex items-center">
                <SubjectChip>{s.name}</SubjectChip>
                <RemoveButton
                  label={s.name}
                  onClick={() =>
                    apply(async () => {
                      let list: WatchItem[] = items;
                      for (const it of s.items) list = await unfollow(session, it.kind, it.value);
                      return list;
                    }, `Could not stop following ${s.name}. Try again.`)
                  }
                />
              </li>
            ))}
          </ul>
        )}

        <section className="grid gap-3" aria-labelledby="rows-title">
          <SectionHead
            id="rows-title"
            title="Stories on your signals"
            sub={ready && todays.length > 0 ? `${todays.length} ${todays.length === 1 ? "story" : "stories"} today · newest first` : undefined}
          />
          {filterChips.length > 0 && (
            <nav className="flex flex-wrap gap-1.5" aria-label="Filter by ticker">
              <Link href="/watchlist" className="p-chip" aria-current={only ? undefined : "page"}>All signals</Link>
              {filterChips.map((t) => (
                <Link key={t} href={tickerHref(t)} className="p-chip" aria-current={only === t ? "page" : undefined}>{`On ${t}`}</Link>
              ))}
            </nav>
          )}
          {!ready ? (
            <div className="grid gap-2.5" aria-label="Loading your signals">
              <span className="p-skel h-24" />
              <span className="p-skel h-24" />
            </div>
          ) : followed === 0 && !only ? (
            <EmptyState title="Nothing followed yet">Follow a ticker or sector above and its stories collect here.</EmptyState>
          ) : (
            <>
              {todays.length > 0 ? (
                <ol className="p-print grid gap-2.5">{todays.map((ev) => <SignalRow key={ev.id} ev={ev} />)}</ol>
              ) : (
                <QuietToday only={only} names={names} last={earlier[0] ?? null} anyEarlier={earlier.length > 0} />
              )}
              {earlier.length > 0 && (
                <div className="grid gap-2.5">
                  <p className="p-eyebrow pt-2">Earlier</p>
                  <ol className="p-print grid gap-2.5">{earlier.map((ev) => <SignalRow key={ev.id} ev={ev} />)}</ol>
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}

/** The three quiet states, each claiming only what the list in hand can back. */
function QuietToday({ only, names, last, anyEarlier }: { only: string | null; names: string[]; last: WatchEvent | null; anyEarlier: boolean }) {
  if (only) {
    return (
      // The way back to every signal is the "All signals" chip right above.
      <EmptyState title={`No stories on ${only} today`}>
        {last ? `The last story naming ${only} was updated on ${shortDate(last.last_updated_at)}.` : `No recent story on your signals names ${only}.`}
      </EmptyState>
    );
  }
  if (!anyEarlier) return <EmptyState title="No recent stories on your signals yet" />;
  return (
    <EmptyState title="No stories on your signals today">
      {`No story on ${names.length > 1 ? `${names.slice(0, -1).join(", ")} or ${names[names.length - 1]}` : names[0]} has been updated since midnight IST. Earlier ones are below.`}
    </EmptyState>
  );
}

function RemoveButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button type="button" onClick={onClick} aria-label={`Stop following ${label}`} className="p-iconbtn">
      <Close />
    </button>
  );
}

/** Follow a ticker (typed, checked in words before it is sent) or one of the six subjects. */
function FollowForm({ following, subjects, onTicker, onSubject }: {
  following: string[];
  subjects: string[];
  onTicker: (symbol: string) => Promise<boolean>;
  onSubject: (sectors: string[], name: string) => Promise<boolean>;
}) {
  const [kind, setKind] = useState<"ticker" | "sector">("ticker");
  const [value, setValue] = useState("");
  const [subject, setSubject] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (kind === "ticker") {
      const v = value.trim().toUpperCase();
      const p = symbolProblem(v, following);
      if (p) return setError(p);
      setBusy(true);
      if (await onTicker(v)) setValue("");
    } else {
      const g = SECTOR_GROUPS.find((x) => x.slug === subject);
      if (!g) return setError("Choose a subject to follow.");
      if (subjects.includes(g.slug)) return setError(`You already follow ${g.name}.`);
      setBusy(true);
      if (await onSubject(g.sectors, g.name)) setSubject("");
    }
    setBusy(false);
  }

  const button = (
    <button type="submit" disabled={busy} aria-busy={busy || undefined} className="p-btn p-btn--primary">
      {busy ? "Following…" : "Follow"}
    </button>
  );
  return (
    <form onSubmit={submit} noValidate className="grid gap-2.5" aria-label="Follow a ticker or a subject">
      <div className="p-seg justify-self-stretch sm:justify-self-start" role="tablist" aria-label="Follow a">
        {(["ticker", "sector"] as const).map((k) => (
          <button key={k} type="button" role="tab" aria-selected={kind === k} className="flex-1 justify-center sm:flex-none" onClick={() => { setKind(k); setError(null); }}>
            {k === "ticker" ? "Ticker" : "Sector"}
          </button>
        ))}
      </div>
      <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-2">
        {kind === "ticker" ? (
          <TextField
            label="NSE or BSE symbol"
            placeholder="e.g. RELIANCE"
            autoCapitalize="characters"
            autoComplete="off"
            spellCheck={false}
            value={value}
            onChange={(v) => { setValue(v); if (error) setError(null); }}
            error={error ?? undefined}
          />
        ) : (
          <div className="grid gap-1.5">
            <SelectField label="Subject" value={subject} onChange={(v) => { setSubject(v); if (error) setError(null); }} options={[{ value: "", label: "Choose a subject" }, ...SECTOR_GROUPS.map((g) => ({ value: g.slug, label: g.name }))]} />
            {error && <p className="p-field__error">{error}</p>}
          </div>
        )}
        <div className="pt-[26px]">{button}</div>
      </div>
    </form>
  );
}

function SignedOut() {
  return (
    <div className={SHELL}>
      <Masthead dateline="Watchlist" />
      <div className="grid gap-[22px] pt-4 lg:pt-9">
        <h1 className={TITLE} style={{ letterSpacing: "var(--track-display)" }}>Watchlist</h1>
        <section className="grid gap-3 py-5" style={{ borderTop: "var(--rule-section) solid var(--ink)" }} aria-labelledby="follow-title">
          <h2 id="follow-title" className="text-balance" style={{ font: "var(--t-display-m)", letterSpacing: "var(--track-display)" }}>Follow a company or a subject</h2>
          <p style={{ font: "var(--t-body)", color: "var(--ink-2)" }}>
            Free with an account. Every story that names what you follow collects here, newest first, with the catalyst when the reports give one.
          </p>
          <Link href="/signin?next=/watchlist" className="p-btn p-btn--primary p-btn--lg p-btn--block sm:w-auto sm:justify-self-start">Sign in to follow</Link>
          <p style={{ font: "400 13px/1.5 var(--font-read)", color: "var(--ink-3)" }}>
            Market Pulse is free without an account. <Link href="/pulse" className="p-link">Open Market Pulse →</Link>
          </p>
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
